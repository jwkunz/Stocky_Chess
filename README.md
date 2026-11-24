# Stocky Chess

A desktop chess program written in Python with a PyQt6 interface. You can play against any
UCI-compatible chess engine (such as [Stockfish](https://stockfishchess.org/) or
[Plum Chess](https://github.com/jwkunz/Plum_Chess)) at an adjustable strength, play another person
on the same computer, or pit two independent, heterogeneous UCI engines against each other with
optional chess clocks.

The rules of chess — including move generation, check detection, castling, en passant, pawn
promotion, threefold repetition, the fifty-move rule, and insufficient-material draws — are
implemented natively in this project. UCI engines are run in a non-blocking background harness to
choose computer moves.

## Features

- **Heterogeneous human and bot players.** White and Black can each be set independently to
  *Is Human* or *Is Bot*, and each bot player can be configured with its own UCI engine, skill
  level (1–20, automatically clamped to the engine's supported range), and search depth (1–30).
- **Engine discovery and one-click GitHub downloads.** Use **Game > Select Engine...** (or the
  per-player bot configuration dialog) to scan your system for installed UCI engines or download
  the latest release of **Stockfish** (`official-stockfish/Stockfish`) or **Plum Chess**
  (`jwkunz/Plum_Chess`) for your OS and CPU architecture directly into the system temporary
  directory (`<tempdir>/stocky_chess_engines`).
- **Start / Pause Bot control.** Bot play starts paused after configuration so both players and
  clocks can be set up before clicking **START BOT** (or **Game > Start / Pause Bot**).
- **Clickable board.** Click a piece to see its legal moves highlighted, then click a destination
  (or click the same piece again to deselect). A dialog offers the piece choice when a pawn promotes.
- **Chess clocks.** Set the starting time (hours, minutes, seconds) and a per-move increment for each
  player, or turn the clock off. Because engine searches run asynchronously in a background thread,
  the GUI and chess clocks update smoothly every 100 ms during bot vs. bot games.
- **Game end detection.** Checkmate, stalemate, threefold repetition draws, fifty-move draws,
  insufficient-material draws, and loss on time are announced.
- **Move history & branching.** Step backward and forward through the game with the **PREVIOUS** and
  **NEXT** buttons, and play a new move from any historical position to branch the game.
- **FEN & PGN support.** The current position is shown as a validated FEN string, any valid position
  can be loaded with **Game > Import FEN**, and full games can be exported in Standard Algebraic
  Notation with **Game > Export PGN**.
- **Material count.** A panel shows the active pieces and material balance for each side.
- **Flip the board** to put either color at the bottom.

## Prebuilt Binaries

Prebuilt standalone executables for **Linux (`x86_64`)**, **Windows (`x86_64`)**, and
**macOS (`arm64`)** are automatically built with PyInstaller and published on every tagged release:

1. Visit the [**Releases**](https://github.com/jwkunz/Stocky_Chess/releases) tab on GitHub.
2. Download the executable matching your operating system (`stocky_chess-linux-x86_64`,
   `stocky_chess-windows-x86_64.exe`, or `stocky_chess-macos-arm64`).
3. On Linux or macOS, mark the binary as executable (`chmod +x stocky_chess-*`) and run it.

## Requirements (Running from Source)

- Python 3.10 or newer
- Dependencies listed in `requirements.txt` (`PyQt6`, `pytest`, `sphinx`, `sphinx-rtd-theme`)

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

1. Run the program from the repository's top-level folder:

   ```sh
   .venv/bin/python src/main.py
   ```

2. Optional: Open **Game > Select Engine...** to scan your system for UCI engines or click
   **Download Latest Release** to fetch Stockfish or Plum Chess from GitHub into the system
   temporary directory.
3. Use **Game > White Player...** and **Black Player...** to set each side to *Is Human* or *Is Bot*
   (selecting the engine, skill level, and search depth independently for each bot), configure
   clocks via **Time Control...**, and click **START BOT** when ready.

## Testing

Run the `pytest` suite from the repository root:

```sh
.venv/bin/pytest
```

## Project layout

| File | Purpose |
|---|---|
| `src/main.py` | The main window, menus, dialogs, clocks, and non-blocking event/engine loop |
| `src/chessState.py` | Board state representation with validated FEN reading and writing |
| `src/chessAdmin.py` | Move generation, attack detection, castling, en passant, promotion, and game-over/draw detection |
| `src/chessBoard.py` | The board widget that draws squares, pieces, coordinates, and highlighted moves |
| `src/gameClickHandler.py` | State machine turning human clicks and engine replies into moves |
| `src/gameLog.py` | History of board positions for stepping through and branching a game |
| `src/uciEngine.py` | Cross-platform UCI engine discovery, GitHub downloader, option parser, and threaded search harness |
| `src/stockfishTerminalPlay.py` | Standalone terminal interface for playing against a UCI engine |
| `resources/` | Qt Designer interface file (`StockyChess.ui`) and chess piece sprite sheet (`ChessPieces.png`) |
| `tests/` | Unit and integration test suite (`pytest`) |
| `docs/` | Sphinx API documentation sources |

## Documentation

API documentation generated with Sphinx is hosted on GitHub Pages at
[https://jwkunz.github.io/Stocky_Chess/](https://jwkunz.github.io/Stocky_Chess/).

## License

Released under the GNU General Public License v3.0. See [LICENSE](LICENSE).
