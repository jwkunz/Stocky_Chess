"""Unit tests for chessState and gameLog modules."""

import pytest
from chessState import chessState, player_t, piece_t, START_FEN
from gameLog import gameLog


def test_starting_state_fen(starting_state: chessState):
    """Verify starting position FEN serialization and attributes."""
    assert starting_state.getFENstring() == START_FEN
    assert starting_state.turn == "w"
    assert starting_state.castle_white_king is True
    assert starting_state.castle_white_queen is True
    assert starting_state.castle_black_king is True
    assert starting_state.castle_black_queen is True
    assert starting_state.enpassant_targets == "-"
    assert starting_state.half_move == 0
    assert starting_state.full_move == 1
    assert starting_state.pieceList[0] == "r"
    assert starting_state.pieceList[4] == "k"
    assert starting_state.pieceList[60] == "K"
    assert starting_state.pieceList[63] == "R"


def test_fen_roundtrip(fen_state):
    """Verify custom FEN strings parse and serialize back identically."""
    custom_fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    state = fen_state(custom_fen)
    assert state.getFENstring() == custom_fen

    ep_fen = "rnbqkbnr/pppp1ppp/8/4pP2/8/8/PPPPP1PP/RNBQKBNR w KQkq e6 0 3"
    ep_state = fen_state(ep_fen)
    assert ep_state.enpassant_targets == "E6"
    assert ep_state.getFENstring() == ep_fen


def test_invalid_fen_raises(empty_state: chessState):
    """Verify malformed FEN strings raise ValueError."""
    with pytest.raises(ValueError):
        empty_state.setFENstring("")
    with pytest.raises(ValueError):
        empty_state.setFENstring("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -")
    with pytest.raises(ValueError):
        empty_state.setFENstring("8/8/8/8/8/8/8 w - - 0 1")
    with pytest.raises(ValueError):
        empty_state.setFENstring("8/8/8/8/8/8/8/9 w - - 0 1")
    with pytest.raises(ValueError):
        empty_state.setFENstring("8/8/8/8/8/8/8/8 x - - 0 1")
    with pytest.raises(ValueError):
        empty_state.setFENstring("8/8/8/8/8/8/8/8 w KQx - 0 1")
    with pytest.raises(ValueError):
        empty_state.setFENstring("8/8/8/8/8/8/8/8 w - e5 0 1")


def test_state_copy_and_equality(starting_state: chessState):
    """Verify chessState.copy creates an independent clone and equality works."""
    cloned = starting_state.copy()
    assert cloned == starting_state
    cloned.pieceList[0] = None
    assert cloned != starting_state
    assert starting_state.pieceList[0] == "r"


def test_toggle_turn(starting_state: chessState):
    """Verify toggle_turn alternates players and increments full_move after Black."""
    assert starting_state.turn == "w"
    assert starting_state.full_move == 1
    starting_state.toggle_turn()
    assert starting_state.turn == "b"
    assert starting_state.full_move == 1
    starting_state.toggle_turn()
    assert starting_state.turn == "w"
    assert starting_state.full_move == 2


def test_game_log_operations(fresh_game_log: gameLog, fen_state):
    """Verify gameLog stores isolated copies, navigates indices, and prunes history."""
    assert fresh_game_log.getCurrentIndex() == 0
    s1 = fen_state("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
    fresh_game_log.addState(s1)
    assert fresh_game_log.getCurrentIndex() == 1

    # Mutating s1 externally should not mutate stored log entry
    s1.turn = "w"
    assert fresh_game_log.getLatestGame().turn == "b"

    s2 = fen_state("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2")
    fresh_game_log.addState(s2)
    assert fresh_game_log.getCurrentIndex() == 2

    fresh_game_log.pruneAfterIndex(1)
    assert fresh_game_log.getCurrentIndex() == 1
    assert fresh_game_log.getGameByIndex(1).turn == "b"


def test_enums():
    """Verify player_t and piece_t enum values."""
    assert player_t.BLACK.value == 0
    assert player_t.WHITE.value == 1
    assert piece_t.KING.value == 0
    assert piece_t.PAWN.value == 5
