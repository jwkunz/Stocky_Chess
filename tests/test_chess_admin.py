"""Comprehensive unit tests for chessAdmin move generation, special rules, and game-over logic."""

import pytest
from chessState import chessState
from chessAdmin import (
    chessMove,
    convertIndex,
    convertLabel,
    convertColRow,
    getAllLegalMoves,
    getMovesFromSquare,
    hasInsufficientMaterial,
    hasKingCollision,
    isFiftyMoveRule,
    isGameOver,
    isSquareAttacked,
    isThreefoldRepetition,
    movePiece,
    squareUp,
    squareDown,
    squareLeft,
    squareRight,
)


def test_coordinate_conversions():
    """Verify algebraic coordinate conversions round-trip accurately."""
    col, row, idx = convertLabel("a8")
    assert (col, row, idx) == (0, 0, 0)
    assert convertIndex(0) == (0, 7, "A8")

    col, row, idx = convertLabel("h1")
    assert (col, row, idx) == (7, 7, 63)
    assert convertIndex(63) == (7, 0, "H1")

    assert convertColRow(4, 4) == (36, "E4")


def test_initial_position_has_20_moves(starting_state: chessState):
    """Verify standard chess starting position generates 20 legal moves for White."""
    moves = getAllLegalMoves(starting_state)
    assert len(moves) == 20


def test_fools_mate_checkmate(fen_state):
    """Verify Fool's Mate is detected as checkmate (isGameOver == 1)."""
    state = fen_state("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
    assert hasKingCollision(state) is True
    assert isGameOver(state) == 1


def test_stalemate_detection(fen_state):
    """Verify classic stalemate position returns isGameOver == 2."""
    state = fen_state("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert hasKingCollision(state) is False
    assert isGameOver(state) == 2


def test_insufficient_material_detection(fen_state):
    """Verify K vs K and K+N vs K are detected as draws by insufficient material."""
    kvk = fen_state("8/8/4k3/8/8/4K3/8/8 w - - 0 1")
    assert hasInsufficientMaterial(kvk) is True
    assert isGameOver(kvk) == 2

    knvk = fen_state("8/8/4k3/8/3N4/4K3/8/8 w - - 0 1")
    assert hasInsufficientMaterial(knvk) is True
    assert isGameOver(knvk) == 2

    krvk = fen_state("8/8/4k3/8/3R4/4K3/8/8 w - - 0 1")
    assert hasInsufficientMaterial(krvk) is False


def test_en_passant_push_and_capture(fen_state):
    """Verify double pawn push sets en passant target and opposing pawn can capture en passant."""
    state = fen_state("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
    # Black plays f7-f5 (index 13 to 29)
    f7_moves = getMovesFromSquare(13, state)
    double_push = [m for m in f7_moves if m.end == 29][0]
    assert double_push.enpassantFlag is True

    movePiece(double_push, state)
    assert state.enpassant_targets == "F6"

    # White pawn on e5 (index 28) captures en passant on f6 (index 21)
    e5_moves = getMovesFromSquare(28, state)
    ep_captures = [m for m in e5_moves if m.end == 21]
    assert len(ep_captures) == 1
    ep_move = ep_captures[0]
    assert ep_move.is_capture is True
    assert ep_move.enpassantFlag is True

    movePiece(ep_move, state)
    assert state.pieceList[21] == "P"
    assert state.pieceList[29] is None
    assert state.enpassant_targets == "-"


def test_castling_and_attack_restrictions(fen_state):
    """Verify kingside/queenside castling and blocking when transit squares are attacked or occupied."""
    # Open rank for both sides castling
    state = fen_state("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    king_moves = getMovesFromSquare(60, state)
    castle_ends = {m.end for m in king_moves if m.castleRookSquares}
    assert castle_ends == {62, 58}

    # Place Black pawn on f3 (index 45) attacking e2/g2, and Black pawn on f2 (index 53) attacking e1/g1
    pawn_attack_state = fen_state("r3k2r/8/8/8/8/8/5p2/R3K2R w KQkq - 0 1")
    assert isSquareAttacked(60, False, pawn_attack_state) is True
    assert [m for m in getMovesFromSquare(60, pawn_attack_state) if m.castleRookSquares] == []

    # Black pawn on g2 (index 54) attacks f1 (index 61, transit square for kingside castle)
    transit_attack_state = fen_state("r3k2r/8/8/8/8/8/6p1/R3K2R w KQkq - 0 1")
    castle_ends_2 = {m.end for m in getMovesFromSquare(60, transit_attack_state) if m.castleRookSquares}
    assert 62 not in castle_ends_2
    assert 58 in castle_ends_2

    # Piece on b1 (index 57) blocks White queenside castle
    b1_blocked_state = fen_state("r3k2r/8/8/8/8/8/8/Rn2K2R w KQkq - 0 1")
    castle_ends_3 = {m.end for m in getMovesFromSquare(60, b1_blocked_state) if m.castleRookSquares}
    assert 58 not in castle_ends_3


def test_rook_capture_revokes_castling_rights(fen_state):
    """Verify capturing an unmoved rook revokes that corner's castling right."""
    state = fen_state("r3k2r/8/8/8/8/8/8/R3K1NR b KQkq - 0 1")
    # Black rook on a8 (0) captures White rook on a1 (56)
    r_moves = getMovesFromSquare(0, state)
    capture_a1 = [m for m in r_moves if m.end == 56][0]
    movePiece(capture_a1, state)
    assert state.castle_white_queen is False
    assert state.castle_white_king is True
    assert state.castle_black_queen is False


def test_pawn_promotion_generates_only_four_choices_with_capture_flag(fen_state):
    """Verify pawn reaching the 8th rank only produces Q, R, B, N promotion moves."""
    state = fen_state("1n2k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    moves = getMovesFromSquare(8, state)
    forward_moves = [m for m in moves if m.end == 0]
    capture_moves = [m for m in moves if m.end == 1]

    assert len(forward_moves) == 4
    assert {m.promotionPiece for m in forward_moves} == {"Q", "R", "B", "N"}
    assert all(not m.is_capture for m in forward_moves)

    assert len(capture_moves) == 4
    assert {m.promotionPiece for m in capture_moves} == {"Q", "R", "B", "N"}
    assert all(m.is_capture for m in capture_moves)


def test_fifty_move_rule_and_threefold_repetition(starting_state: chessState):
    """Verify 50-move inaction rule and threefold repetition detection."""
    s50 = starting_state.copy()
    s50.half_move = 99
    assert isFiftyMoveRule(s50) is False
    assert isGameOver(s50) == 0
    s50.half_move = 100
    assert isFiftyMoveRule(s50) is True
    assert isGameOver(s50) == 2

    # Play Ng1-f3, Nb8-c6, Nf3-g1, Nc6-b8 twice to reach the starting position 3 times
    history = [starting_state.copy()]
    current = starting_state.copy()
    cycle = [
        chessMove(62, 45),  # Ng1-f3
        chessMove(1, 18),   # Nb8-c6
        chessMove(45, 62),  # Nf3-g1
        chessMove(18, 1),   # Nc6-b8
    ]
    for move in cycle:
        movePiece(move, current)
        history.append(current.copy())
    # Starting position has appeared twice so far
    assert isThreefoldRepetition(current, history) is False
    assert isGameOver(current, history) == 0

    for move in cycle:
        movePiece(move, current)
        history.append(current.copy())
    # Starting position has now appeared 3 times
    assert isThreefoldRepetition(current, history) is True
    assert isGameOver(current, history) == 2
