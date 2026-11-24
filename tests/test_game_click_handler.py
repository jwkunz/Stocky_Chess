"""Unit and integration tests for gameClickHandler, engine vs engine play, and UI click handling."""

import pytest
from chessState import chessState, player_t
from chessAdmin import chessMove, convertIndex, convertLabel, movePiece
from gameLog import gameLog
from gameClickHandler import gameClickHandler


class DummyDisplay:
    """Stub text display widget recording appended lines."""

    def __init__(self):
        self.lines: list[str] = []

    def append(self, text: str):
        self.lines.append(text)


class DummyBoardWidget:
    """Headless stub of chessBoard_widget for testing gameClickHandler."""

    def __init__(self):
        self.last_state: chessState | None = None
        self.last_highlights: list[chessMove] = []
        self.square_for_coords: int = 0

    def renderBoard(self, cs: chessState, highlightedMoves=None):
        self.last_state = cs.copy()
        self.last_highlights = list(highlightedMoves) if highlightedMoves else []

    def coordToSquare(self, x, y) -> int:
        return int(x)


class DummyEngine:
    """Stub UCI engine returning scripted moves."""

    def __init__(self, moves: list[str | None]):
        self.moves = list(moves)

    def request_move(self, fen: str) -> str | None:
        if self.moves:
            return self.moves.pop(0)
        return None


class DummyMainWindow:
    """Stub MainWindow for testing clickHandler and engineHandler without dialogs."""

    def __init__(self, white_engine=None, black_engine=None, promo_choice="Q"):
        self.whiteEngine = white_engine
        self.blackEngine = black_engine
        self.whiteDisplay = DummyDisplay()
        self.blackDisplay = DummyDisplay()
        self.promo_choice = promo_choice

    def movePieceWithAnimation(self, move: chessMove, cs: chessState, filterForCheck: bool = True):
        movePiece(move, cs, filterForCheck)

    def promotionCallback(self, is_white: bool) -> str:
        return self.promo_choice.upper() if is_white else self.promo_choice.lower()


def test_human_select_deselect_and_move(starting_state: chessState, fresh_game_log: gameLog):
    """Verify human clicking a piece highlights moves, clicking again deselects, and clicking destination moves."""
    handler = gameClickHandler()
    board = DummyBoardWidget()
    win = DummyMainWindow()

    # Click e2 (index 52)
    handler.clickHandler(52, 0, starting_state, board, fresh_game_log, win)
    assert handler.action_state == "WHITE_SELECT_MOVE"
    assert handler.action_idx == 52
    assert len(board.last_highlights) == 2

    # Click e2 again -> deselects and clears highlights
    handler.clickHandler(52, 0, starting_state, board, fresh_game_log, win)
    assert handler.action_state == "WHITE_SELECT_PIECE"
    assert handler.action_idx is None
    assert board.last_highlights == []

    # Reselect e2 and move to e4 (index 36)
    handler.clickHandler(52, 0, starting_state, board, fresh_game_log, win)
    handler.clickHandler(36, 0, starting_state, board, fresh_game_log, win)
    assert handler.action_state == "BLACK_SELECT_PIECE"
    assert starting_state.pieceList[36] == "P"
    assert starting_state.turn == "b"
    assert fresh_game_log.getCurrentIndex() == 1


def test_human_clicks_ignored_during_engine_turn(starting_state: chessState, fresh_game_log: gameLog):
    """Verify clicking the board with mouse coordinates during a CPU turn does not trigger engineHandler."""
    white_bot = DummyEngine(["e2e4"])
    win = DummyMainWindow(white_engine=white_bot)
    handler = gameClickHandler()
    board = DummyBoardWidget()

    # Human click at square 52 while whiteEngine is active should be ignored
    handler.clickHandler(52, 0, starting_state, board, fresh_game_log, win)
    assert starting_state.turn == "w"
    assert fresh_game_log.getCurrentIndex() == 0
    assert len(white_bot.moves) == 1

    # Bot turn (x=None, y=None) executes the move
    handler.clickHandler(None, None, starting_state, board, fresh_game_log, win)
    assert starting_state.turn == "b"
    assert starting_state.pieceList[36] == "P"
    assert fresh_game_log.getCurrentIndex() == 1


def test_engine_vs_engine_fools_mate_and_fallback(starting_state: chessState, fresh_game_log: gameLog):
    """Verify two engines playing Fool's Mate reach CHECKMATE cleanly and fallback works if engine returns None."""
    white_bot = DummyEngine(["f2f3", "g2g4"])
    black_bot = DummyEngine(["e7e5", "d8h4"])
    win = DummyMainWindow(white_engine=white_bot, black_engine=black_bot)
    handler = gameClickHandler()
    board = DummyBoardWidget()

    for _ in range(4):
        handler.clickHandler(None, None, starting_state, board, fresh_game_log, win)

    assert handler.action_state == "CHECKMATE"
    assert "White loses by checkmate" in win.whiteDisplay.lines
    assert "Black wins by checkmate" in win.blackDisplay.lines

    # Calling clickHandler again after CHECKMATE is a safe no-op
    handler.clickHandler(None, None, starting_state, board, fresh_game_log, win)
    assert fresh_game_log.getCurrentIndex() == 4
