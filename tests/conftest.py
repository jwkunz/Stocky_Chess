"""Shared pytest fixtures for the Stocky Chess test suite."""

import pytest
from chessState import chessState
from gameLog import gameLog


@pytest.fixture
def starting_state() -> chessState:
    """Return a fresh chessState initialized to the standard starting position."""
    cs = chessState()
    cs.setNewGame()
    return cs


@pytest.fixture
def empty_state() -> chessState:
    """Return a blank chessState with no pieces and White to move."""
    cs = chessState()
    cs.turn = "w"
    cs.full_move = 1
    return cs


@pytest.fixture
def fen_state():
    """Factory fixture returning a chessState initialized from a custom FEN string."""
    def _make(fen: str) -> chessState:
        cs = chessState()
        cs.setFENstring(fen)
        return cs
    return _make


@pytest.fixture
def fresh_game_log() -> gameLog:
    """Return a reset gameLog containing the initial starting position."""
    gl = gameLog()
    gl.reset()
    return gl
