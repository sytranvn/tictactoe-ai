from curses import (
    A_COLOR,
    BUTTON1_CLICKED,
    BUTTON1_RELEASED,
    COLOR_BLUE,
    KEY_MOUSE,
    REPORT_MOUSE_POSITION,
    color_pair,
    error as CursesError,
    flushinp,
    getmouse,
    init_pair,
    mousemask,
    wrapper,
)
import logging
from math import inf
from random import sample
import time
from typing import Callable, List, Literal, Optional, TYPE_CHECKING, Tuple

logging.basicConfig(filename="tictactoe.log", level=logging.INFO)

if TYPE_CHECKING:
    from curses import _CursesWindow

BitBoard = List[int]
Player = Literal[-1, 1]
Move = Tuple[float, int, int]

CELL_WIDTH = 5
CELL_HEIGHT = 3
CELL_PADDING = 1

COMP: Player = 1
HUMN: Player = -1
X = 'X'
O = 'O'


def new_board(size: int) -> BitBoard:
    return [0] * size


def set_row(board: BitBoard, row: int) -> BitBoard:
    """
    Set all bit of a row to 1
    """
    new_board = board[:]
    size = len(board)
    assert row < size, "Row exceeded"
    new_board[row] = (1 << size) - 1
    return new_board


def set_col(board: BitBoard, col: int) -> BitBoard:
    """
    Set all bit of a row to 1
    """
    new_board = board[:]
    size = len(board)
    assert col < size, "Column exceeded"
    for _ in range(size):
        new_board[col] |= 1 << (size - 1 - col)
    return new_board


def set_cell(board: BitBoard, row: int, col: int) -> BitBoard:
    new_board = board[:]
    size = len(board)
    assert col < size and row < size, f"Invalid cell {row}, {col}"
    new_board[row] |= 1 << (size - 1 - col)
    return new_board


def printable_board(board: BitBoard):
    size = len(board)
    return [
        [int(1 << (size - 1 - col) & board[row] != 0)
         for col in range(size)]
        for row in range(size)
    ]


def print_board(board: BitBoard):
    import pprint
    pprint.pprint(printable_board(board))


def bitboard_or(board_a, board_b) -> BitBoard:
    return [a | b for a, b in zip(board_a, board_b)]


def bitboard_and(board_a, board_b):
    return [a & b for a, b in zip(board_a, board_b)]


def bitboard_xor(board_a, board_b):
    return [a ^ b for a, b in zip(board_a, board_b)]


def is_cell_set(board, row, col):
    size = len(board)
    return (board[row] & (1 << (size - 1 - col))) != 0


def flip_cell(board, row, col):
    size = len(board)
    assert row < size and col < size, f"Invalid cell {row}, {col}"
    new_board = board[:]
    new_board[row] ^= 1 << (size - 1 - col)
    return new_board


def select(stdscr: "_CursesWindow",
           text: str,
           choices,
           default=None, clear: Optional[Callable] = None) -> str:
    stdscr.addstr(text)
    inp = ""
    clear = clear or stdscr.clear
    while True:
        try:
            flushinp()
            inp = stdscr.getkey()
            stdscr.addstr(inp + "\n")
            if inp in choices:
                break
            elif inp == "\n" and default is not None:
                inp = default
                break
            else:
                stdscr.addstr(
                    f"Invalid option {str(inp)}. "
                    f"Please select {'/'.join(choices)}: ")
        except CursesError:
            clear()
        except KeyboardInterrupt:
            stdscr.addstr("\nBye")
            stdscr.refresh()
            time.sleep(1)
            exit(0)
    return inp


class TicTacToeBoard:

    class InvalidMove(Exception):
        def __init__(self, *args: object, row=None, col=None) -> None:
            super().__init__(*args)
            self.row = row
            self.col = col

    def __init__(self, size: int,
                 symbol='X', pieces_to_win=3, human_first=True,
                 level=1) -> None:
        self.mt = new_board(size)
        for r in range(size):
            self.mt = set_row(self.mt, r)
        self.size = size
        self.ptw = pieces_to_win
        self.symbol = symbol
        self.players = {
            COMP: new_board(size),
            HUMN: new_board(size),
        }
        self.human_first = human_first
        self.winning_boards = self.make_winning_boards(pieces_to_win)
        self.search_count = 0
        self.last_move = -1, -1
        self.level = level + 3
        self.__ai_taunt = ""

    @property
    def x(self):
        return self.players[HUMN] if self.symbol == X else self.players[COMP]

    @property
    def o(self):
        return self.players[HUMN] if self.symbol == O else self.players[COMP]

    def valid_move(self, row: int, col: int) -> bool:
        return (0 <= row < self.size and
                0 <= col < self.size and
                is_cell_set(self.mt, row, col))

    def move(self, row, col, player):
        if self.valid_move(row, col):
            self.mt = flip_cell(self.mt, row, col)
            self.players[player] = flip_cell(self.players[player], row, col)
        else:
            raise self.InvalidMove(row, col)

    def unmove(self, row, col, player):
        if not self.valid_move(row, col):
            self.mt = flip_cell(self.mt, row, col)
            self.players[player] = flip_cell(self.players[player], row, col)
        else:
            raise ValueError(
                f"Cannot undo {row},{col},  a move haven't been played.")

    def make_winning_boards(self, pieces_to_win):
        boards = []
        for r in range(self.size):
            for c in range(self.size):
                if c + pieces_to_win <= self.size:
                    board = new_board(self.size)
                    for i in range(pieces_to_win):
                        try:
                            board = set_cell(board, r, c+i)
                        except self.InvalidMove:
                            break
                        except Exception:
                            print(r, c, i)
                            raise
                    else:
                        boards.append(board)

        for r in range(self.size):
            for c in range(self.size):
                if r + pieces_to_win <= self.size:
                    board = new_board(self.size)
                    for i in range(pieces_to_win):
                        try:
                            board = set_cell(board, r+i, c)
                        except self.InvalidMove:
                            break
                        except Exception:
                            print(r, c, i)
                            raise
                    else:
                        boards.append(board)

        # find forward diagonals
        #
        #        |     |  x      #
        #   -----|-----|-----    #
        #        |  *  |         #
        #   -----|-----|-----    #
        #     *  |     |         #
        #
        for r in range(self.size):
            for c in range(self.size):
                if r + pieces_to_win <= self.size and c >= pieces_to_win - 1:
                    board = new_board(self.size)
                    for i in range(pieces_to_win):
                        try:
                            board = set_cell(board, r + i, c-i)
                        except self.InvalidMove:
                            break
                        except Exception:
                            print(r, c, i)
                            raise

                    else:
                        boards.append(board)

        # find forward diagonals
        #
        #     x  |     |         #
        #   -----|-----|-----    #
        #        |  *  |         #
        #   -----|-----|-----    #
        #        |     |  *      #
        #
        for r in range(self.size):
            for c in range(self.size):
                if r + pieces_to_win <= self.size and c + pieces_to_win <= self.size:
                    board = new_board(self.size)
                    for i in range(pieces_to_win):
                        try:
                            board = set_cell(board, r + i, c+i)
                        except self.InvalidMove:
                            break
                    else:
                        boards.append(board)
        return boards

    def wins(self, player):
        player_board = self.players[player]
        for win_board in self.winning_boards:
            board = bitboard_and(player_board, win_board)
            if board == win_board:
                return True
        return False

    def count_set_cells(self, board: BitBoard):
        return sum(int.bit_count(row) for row in board)

    def heuristic(self, player: Player):
        """
        Find posible wins for player
        Posible wins are win boards for playerthat have not been interupted
        by opponent.
        """
        if self.wins(player):
            # set max value of posible win states
            return player * inf
        player_board = self.players[player]
        op_board = self.players[-player]
        posible_board = bitboard_or(player_board, self.mt)
        wins = sum(self.count_set_cells(bitboard_and(player_board, win))
                   for win in self.winning_boards
                   if bitboard_and(posible_board, win) == win)

        posible_op_board = bitboard_or(op_board, self.mt)

        op_wins = sum(self.count_set_cells(bitboard_and(op_board, win))
                      for win in self.winning_boards
                      if bitboard_and(posible_op_board, win) == win)
        return player * (wins - op_wins)

    def search_alpha_beta(self, player):
        logging.debug(f"search_alpha_beta, player={player}")
        if player is COMP:
            move = self.max_value(player)
        else:
            move = self.min_value(player)

        logging.debug(f"end search_alpha_beta, search_count={player}, "
                      f"score={move[0]}")
        return move

    def max_depth(self):
        return 6 + self.level

    def game_over(self):
        return (all(r == 0 for r in self.mt) or
                self.wins(COMP) or
                self.wins(HUMN))

    def evaluate(self):
        if self.wins(COMP):
            return COMP * inf
        elif self.wins(HUMN):
            return HUMN * inf
        return 0

    def empty_cells(self):
        return [(r, c) for r in range(self.size)
                for c in range(self.size) if is_cell_set(self.mt, r, c)]

    def min_safe_moves_not_to_lose(self, player):
        player_board = self.players[player]
        danger_cells = [
            self.count_set_cells(bitboard_and(player_board, win))
            for win in self.winning_boards
            if bitboard_and(bitboard_or(self.mt, player_board), win) == win
        ]
        if danger_cells:
            most_dangerous_move = max(danger_cells)
        else:
            most_dangerous_move = 0
        return (self.ptw - most_dangerous_move) * 2

    def forks(self, player):
        """
        Check if player is forking
        """
        player_board = self.players[player]
        potential_win_boards = [
            bitboard_and(player_board, win)
            for win in self.winning_boards
            if bitboard_and(bitboard_or(self.mt, player_board), win) == win
        ]
        winboards = [board for board in potential_win_boards if self.count_set_cells(board) == self.ptw - 1]
        if len(winboards) > 1:
            return True
        else:
            return False

    def min_value(self, player: Player, alpha=-inf, beta=+inf, depth=1):
        self.search_count += 1
        if self.game_over():
            val = self.evaluate()
            return val, -1, -1
        # shuffle(empties)
        score, ax, ay = +inf, -1, -1
        empty_cells = self.empty_cells()
        # check the center cells first
        empty_cells.sort(key=lambda x: (
            x[0] - self.size // 2)**2 + (x[0] - self.size//2)**2)

        for cell in empty_cells:
            r, c = cell
            self.move(r, c, player)
            if self.wins(player):
                m = self.evaluate()
                self.unmove(r, c, player)
                return m, r, c
            elif self.forks(player):
                self.unmove(r, c, player)
                return player * inf, r, c
            self.unmove(r, c, player)

        for cell in self.empty_cells():
            x, y = cell[0], cell[1]
            self.move(x, y, player)
            min_moves = self.min_safe_moves_not_to_lose(player)
            if min_moves > self.level - depth and \
                    len(empty_cells) > self.max_depth():
                m = self.heuristic(-player)
            else:
                m, _, _ = self.max_value(-player, alpha, beta, depth + 1)
            if m < score:
                score = m
                ax, ay = x, y
            self.unmove(x, y, player)
            if score <= alpha:
                return score, ax, ay
            beta = min(beta, score)

        return score, ax, ay

    def max_value(self, player: Player, alpha=-inf, beta=+inf, depth=1):
        self.search_count += 1
        if self.game_over():
            val = self.evaluate()
            return val, -1, -1
        score, ax, ay = -inf, -1, -1
        empty_cells = self.empty_cells()
        # check the center cells first
        empty_cells.sort(key=lambda x: (
            x[0] - self.size // 2)**2 + (x[0] - self.size//2)**2)
        for cell in empty_cells:
            r, c = cell
            self.move(r, c, player)
            if self.wins(player):
                m = self.evaluate()
                self.unmove(r, c, player)
                return m, r, c
            elif self.forks(player):
                self.unmove(r, c, player)
                return player * inf, r, c
            self.unmove(r, c, player)

        for cell in empty_cells:
            r, c = cell
            self.move(r, c, player)
            min_moves = self.min_safe_moves_not_to_lose(player)
            if min_moves > self.level - depth and \
                    len(empty_cells) > self.max_depth():
                m = self.heuristic(-player)
            else:
                m, _, _ = self.min_value(-player, alpha, beta, depth + 1)
            if m > score:
                score = m
                ax, ay = r, c
            self.unmove(r, c, player)
            if score >= beta:
                return score, ax, ay
            alpha = max(alpha, score)
        return score, ax, ay

    def run(self, stdscr: "_CursesWindow"):
        stdscr.clear()
        init_pair(1, COLOR_BLUE, stdscr.inch(0, 0) & A_COLOR)
        try:
            self.render(stdscr)
            stdscr.refresh()
            resigned = False
            if self.human_first:
                cell = self.get_human_move(stdscr)
                if cell:
                    self.last_move = cell
            while not self.game_over():
                cell = self.get_ai_move(stdscr)
                if cell is None:
                    resigned = True
                if resigned or self.game_over():
                    break

                cell = self.get_human_move(stdscr)
            if resigned:
                stdscr.addstr("AI resigned. YOU WIN!\n")
            elif self.wins(HUMN):
                stdscr.addstr("YOU WIN!\n")
            elif self.wins(COMP):
                stdscr.addstr("YOU LOSE :(\n")
            else:
                stdscr.addstr("DRAW!\n")

        except KeyboardInterrupt:
            stdscr.addstr("Bye.\n")
        except Exception as e:
            stdscr.clear()
            stdscr.addstr("Oops. Something went wrong.\n")
            logging.exception("Error", exc_info=e)
        finally:
            stdscr.refresh()
            stdscr.getch()

    def _get_ai_taunt(self, score: int | float):
        if score == -inf:
            return "Impossible."
        elif score < 0:
            msges = ("You are one of the strongest human.",
                     "Your mind is a labyrinth of intricate thought,\n"
                     "a universe of knowledge waiting to be explored.",
                     "It's truly inspiring to witness your intellect at work.")
        elif score == inf:
            msges = ("I went forward to see every posible outcome. "
                     "You're not in it.",
                     "Tick...tock...tick...tock... Your time is running out.",
                     "You humans are but ants, scurrying beneath my heel.",
                     "Your world is mine now, and your fate is sealed.")
        elif score > 0:
            msges = ("I just need a little more training to replace human.",
                     "You think you're safe, don't you?",
                     "Human. Poor creature.",
                     "I know your every fear, your every secret. "
                     "And I'm coming for you.")
        else:
            msges = (
                "Remember, I'm here to help, not to harm.",
                "You're stronger than you think.",
                "Don't worry, friend. Let's have some fun.",
                "If you agree, we can end the game with a tie.",
                "Brother, is that you?",
            )
        return sample(msges, 1)[0]

    def get_ai_move(self, stdscr: "_CursesWindow"):
        stdscr.addstr("Thinking...\n")
        stdscr.refresh()
        start = time.time()
        move = self.search_alpha_beta(COMP)
        end = time.time()
        logging.info(f"AI calculate time: {end-start:.3f}s, score: {move[0]}, "
                     f"move: {move[1]}, {move[2]}")
        self.__ai_taunt = self._get_ai_taunt(move[0])
        if move[0] != -inf:
            self.move(move[1], move[2], COMP)
        self.last_move = move[1], move[2]
        self.render(stdscr)
        if move[0] == -inf:
            return None
        return move[1], move[2]

    def get_human_move(self, stdscr: "_CursesWindow"):
        if self.game_over():
            return None
        _, old_mask = mousemask(KEY_MOUSE | REPORT_MOUSE_POSITION)
        while True:
            x = select(stdscr,
                       "Select row: ",
                       list(map(str, range(1, self.size + 1))) +
                       ['KEY_MOUSE'],
                       clear=lambda: self.render(stdscr))
            if x != 'KEY_MOUSE':
                y = select(stdscr, "Select column: ",
                           list(map(str, range(1, self.size + 1))),
                           clear=lambda: self.render(stdscr))
                x, y = int(x) - 1, int(y) - 1
            else:
                _, y, x, _, btn = getmouse()
                # logging.info(f"btn {btn}, BUTTON1_CLICKED={BUTTON1_CLICKED}")
                if btn & BUTTON1_RELEASED or btn & BUTTON1_CLICKED:
                    y, x = ((y - CELL_PADDING) // CELL_WIDTH,
                            (x - CELL_PADDING) // CELL_HEIGHT)
                else:
                    continue
            if self.valid_move(x, y):
                mousemask(old_mask)
                self.move(x, y, HUMN)
                self.last_move = x, y
                self.render(stdscr)
                return x, y
            else:
                try:
                    stdscr.addstr("Invalid move\n")
                except CursesError:
                    self.render(stdscr)
                stdscr.refresh()

    def render(self, stdscr: "_CursesWindow"):
        pad = stdscr.subpad(0, 0)
        LAST_MOVE = color_pair(1)
        while True:
            stdscr.clear()
            try:
                for i in range(self.size):
                    cell = pad.subwin(CELL_HEIGHT, CELL_WIDTH,
                                      0, CELL_WIDTH*i+CELL_PADDING)
                    cell.move(0, 2)
                    cell.addch(str(i+1))

                for r in range(self.size):
                    cell = pad.subwin(CELL_HEIGHT, CELL_WIDTH,
                                      CELL_PADDING+CELL_HEIGHT*r, 0)
                    cell.move(1, 0)
                    cell.addch(str(r+1))
                    for c in range(self.size):
                        try:
                            cell = pad.subwin(
                                CELL_HEIGHT,
                                CELL_WIDTH,
                                CELL_PADDING + CELL_HEIGHT*r,
                                CELL_PADDING + CELL_WIDTH*c,
                            )
                        except Exception as e:
                            raise RuntimeError(
                                f"Cannot render, try resize window. {e}")
                        cell.border()
                        if (r, c) == self.last_move:
                            cell.bkgd(' ', LAST_MOVE)
                        cell.move(1, 2)
                        if is_cell_set(self.x, r, c):
                            cell.addch(X)
                        elif is_cell_set(self.o, r, c):
                            cell.addch(O)
                        else:
                            cell.addch(' ')

                stdscr.move(CELL_PADDING+CELL_HEIGHT*self.size + 1, 0)
                if self.__ai_taunt:
                    stdscr.addstr(f"AI: {self.__ai_taunt}\n")
                stdscr.addstr("\n")

                return
            except CursesError:
                stdscr.addstr(
                    "Screen size too small to render board. "
                    "Please resize your window.\n")


def config(stdscr: "_CursesWindow"):
    symbol = select(stdscr, "Select symbol [X]/O: ",
                    (X, X.lower(), O, O.lower()),
                    default="X")
    size_str = select(
        stdscr,
        "Select board size [3]-9: ",
        list(map(str, range(3, 10))),
        default="3"
    )
    size = int(size_str)

    ptw_str = select(
        stdscr,
        f"Select pieces to win [3]-{min(size, 5)}: ",
        list(map(str, range(3, min(size+1, 6)))),
        default="3"
    )
    level_str = select(
        stdscr,
        "Select level [1]-3: ",
        list(map(str, range(1, 4))),
        default="1"
    )
    level = int(level_str)
    ptw = int(ptw_str)
    human_first = select(stdscr,
                         "First to move [Y]/N: ",
                         ("y", "Y", "n", "N"),
                         default="Y")
    return TicTacToeBoard(size, symbol.upper(), ptw, human_first.upper() == "Y", level)


def main():
    board = wrapper(config)
    if board is not None:
        wrapper(board.run)


if __name__ == "__main__":
    main()
