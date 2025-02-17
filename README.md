# tic-tac-toe

Tic-tac-toe game against my AI.

<video src="https://github.com/user-attachments/assets/2db1d74c-1761-4233-bda1-eeefe1d24cd6">
[demo](assets/output.mov)
</video>

## Algorithm used

### Alpha–beta pruning

[Alpha–beta pruning](https://en.wikipedia.org/wiki/Alpha%E2%80%93beta_pruning).

### Minimax

If current position is wins or lose to a player. Return `inf/-inf`
accordingly.

Otherwise, try all possible moves from center of the board. If AI can
win with a move, take that move immediately. If in 5 moves, we find a
way for human to win with a fork attack, we have to prevent it.
Therefore we have to check terminal state with 5 level deep. If we
ensure we will not lose in 5 moves, use `heuristic` function to
consider next move to save time.

### Heuristic evaluation

Find all possible wins from current position by assuming we will
occupy the remaining empty cells. From those winning states, count how
many cell we had set.

Do the same for opponent and subtract to get heuristic value.

![heuristic](assets/heuristic.png)


## Game state optimization

Instead of using 2D list. We use single list as rows of the board and
manage column using bitwise operators. We can use single number and go
full bitwise but with 9x9 board, it will be 81 bits. Even though
python can expand variable bits for us. I just don't like it.

# For Windows

Windows user must install `windows-curses` by `pip install windows-curses`. 

## Disclaimer

Clicking is supported but might not work properly on Windows . And I
don't care.
