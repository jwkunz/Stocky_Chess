# Stocky Chess

A desktop chess program written in Python with a PyQt6 interface. You can play against the
[Stockfish](https://stockfishchess.org/) engine at an adjustable strength, play another person on
the same computer, or watch Stockfish play itself, with optional chess clocks.

The rules of chess, including move generation, check detection, castling, en passant, and pawn
promotion, are implemented in this project. Stockfish is used only to choose the computer's moves,
through the standard UCI protocol.

## Features

- **Play any combination of human and engine.** Each side is set to *Human* or *Stockfish*
  independently, so you can play either color, play a friend, or let two engines play each other.
- **Adjustable engine strength.** For each Stockfish player you choose a skill level from 1 to 20
  and a search depth from 1 to 30.
- **Clickable board.** Click a piece to see its legal moves highlighted, then click a destination.
  Moves are animated, and a dialog offers the piece choice when a pawn promotes.
- **Chess clocks.** Set the starting time (hours, minutes, seconds) and a per-move increment for each
  player, or turn the clock off. A player who runs out of time loses.
- **Game end detection.** Checkmate, stalemate, and loss on time are announced.
- **Move history.** Step backward and forward through the game with the Previous and Next buttons.
- **FEN support.** The current position is shown as a FEN string, and any position can be loaded
  with *Import FEN*.
- **Material count.** A panel shows the material on the board for each side.
- **Flip the board** to put either color at the bottom.

## Requirements

- Python 3.10 or newer
- [PyQt6](https://pypi.org/project/PyQt6/)
- A Stockfish executable, only needed to play against the engine. It is not included in this
  repository.

```sh
pip install PyQt6
```

## Running

1. Download Stockfish from [stockfishchess.org](https://stockfishchess.org/download/) and place the
   executable in the repository folder as `stockfish.exe`. The engine path is set in
   `src/uciEngine.py`.
2. Run the program from the repository's top-level folder, so that it can find the `resources`
   folder:

   ```sh
   python src/main.py
   ```

3. Choose **Game > New Game**. Use **Game > White Player...** and **Black Player...** to set each side
   to *Is Human* or *Is Stockfish*, and **Time Control...** to set the clocks.

The engine handshake in `uciEngine.py` works across Windows, Linux, and macOS, and automatically
detects `stockfish` or `stockfish.exe` on your `PATH` or in the repository directory.

## Project layout

| File | Purpose |
|---|---|
| `src/main.py` | The main window, menus, dialogs, clocks, and the game loop |
| `src/chessState.py` | The board state, with FEN reading and writing |
| `src/chessAdmin.py` | Move generation for every piece, check filtering, castling, en passant, promotion, and checkmate and stalemate detection |
| `src/chessBoard.py` | The board widget that draws squares, pieces, and highlighted moves |
| `src/gameClickHandler.py` | Turns clicks and engine replies into moves |
| `src/gameLog.py` | The history of positions used for stepping through a game |
| `src/uciEngine.py` | Starts Stockfish and talks to it over UCI, setting skill level and search depth |
| `src/stockfishTerminalPlay.py` | A terminal-based way to play against Stockfish |
| `resources/` | The Qt Designer interface file and the chess piece images |

## Documentation

API documentation generated with Sphinx is hosted on GitHub Pages at
[https://jwkunz.github.io/Stocky_Chess/](https://jwkunz.github.io/Stocky_Chess/).

## Known limitations

- Draws by threefold repetition are not detected.
- The *Export PGN* menu item is present but not implemented.
- Stockfish must be installed separately.

## License

Released under the GNU General Public License v3.0. See [LICENSE](LICENSE).
