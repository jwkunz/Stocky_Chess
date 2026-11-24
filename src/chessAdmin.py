"""Core chess rules, move generation, check filtering, and game-over evaluation."""

from chessState import chessState, player_t


class chessMove:
    """Represents a candidate or executed chess move and its associated rule flags.

    :ivar start: Starting square index (0..63).
    :vartype start: int
    :ivar end: Destination square index (0..63).
    :vartype end: int
    :ivar is_capture: Whether the move captures an opposing piece.
    :vartype is_capture: bool
    :ivar enpassantFlag: Whether the move is a two-square pawn advance or en passant capture.
    :vartype enpassantFlag: bool
    :ivar is_check: Whether the move directly attacks or delivers check to the opposing king.
    :vartype is_check: bool
    :ivar promotionPiece: FEN character of the promoted piece, or ``''`` if not a promotion.
    :vartype promotionPiece: str
    :ivar castleRookSquares: Two-element list ``[rook_start, rook_end]`` for castling moves.
    :vartype castleRookSquares: list[int]
    """

    def __init__(
        self,
        start: int,
        end: int,
        is_capture: bool = False,
        promotionPiece: str = "",
        enpassantFlag: bool = False,
        is_check: bool = False,
        castleRookSquares: list[int] | None = None,
    ):
        """Initialize a chess move descriptor.

        :param start: Starting board square index (0..63).
        :type start: int
        :param end: Ending board square index (0..63).
        :type end: int
        :param is_capture: True if the move captures an opponent piece.
        :type is_capture: bool
        :param promotionPiece: Promotion piece character (e.g., ``'Q'``, ``'n'``) or ``''``.
        :type promotionPiece: str
        :param enpassantFlag: True if the move triggers or executes en passant.
        :type enpassantFlag: bool
        :param is_check: True if the move targets or checks the opponent's king.
        :type is_check: bool
        :param castleRookSquares: Rook ``[from_idx, to_idx]`` squares when castling.
        :type castleRookSquares: list[int] | None
        """
        self.start = start
        self.end = end
        self.is_capture = is_capture
        self.enpassantFlag = enpassantFlag
        self.is_check = is_check
        self.promotionPiece = promotionPiece
        self.castleRookSquares = list(castleRookSquares) if castleRookSquares else []

    def to_uci(self) -> str:
        """Convert this move to a UCI coordinate string (e.g., ``'e2e4'`` or ``'e7e8q'``).

        :return: Lowercase UCI coordinate move string.
        :rtype: str
        """
        _, _, start_label = convertIndex(self.start)
        _, _, end_label = convertIndex(self.end)
        promo = self.promotionPiece.lower() if self.promotionPiece else ""
        return f"{start_label.lower()}{end_label.lower()}{promo}"

    def __eq__(self, other: object) -> bool:
        """Compare two chessMove instances by coordinates and flags."""
        if not isinstance(other, chessMove):
            return False
        return (
            self.start == other.start
            and self.end == other.end
            and self.promotionPiece == other.promotionPiece
            and self.is_capture == other.is_capture
            and self.enpassantFlag == other.enpassantFlag
            and self.castleRookSquares == other.castleRookSquares
        )


def squareUp(idx: int) -> int:
    """Return the square index one rank up (towards rank 8), or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    if idx < 8 or idx >= 64:
        return 64
    return idx - 8


def squareDown(idx: int) -> int:
    """Return the square index one rank down (towards rank 1), or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    if idx < 0 or idx >= 56:
        return 64
    return idx + 8


def squareLeft(idx: int) -> int:
    """Return the square index one file left (towards file A), or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    if idx < 0 or idx >= 64 or (idx % 8 == 0):
        return 64
    return idx - 1


def squareRight(idx: int) -> int:
    """Return the square index one file right (towards file H), or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    if idx < 0 or idx >= 64 or (idx % 8 == 7):
        return 64
    return idx + 1


def squareUpRight(idx: int) -> int:
    """Return the square index one step diagonally up-right, or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    val = squareRight(idx)
    if val >= 64:
        return 64
    return squareUp(val)


def squareUpLeft(idx: int) -> int:
    """Return the square index one step diagonally up-left, or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    val = squareLeft(idx)
    if val >= 64:
        return 64
    return squareUp(val)


def squareDownRight(idx: int) -> int:
    """Return the square index one step diagonally down-right, or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    val = squareRight(idx)
    if val >= 64:
        return 64
    return squareDown(val)


def squareDownLeft(idx: int) -> int:
    """Return the square index one step diagonally down-left, or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    val = squareLeft(idx)
    if val >= 64:
        return 64
    return squareDown(val)


def getCollisionType(from_index: int, to_index: int, cs: chessState) -> int:
    """Classify the interaction of moving a piece from ``from_index`` to ``to_index``.

    :param from_index: Origin square index (0..63).
    :type from_index: int
    :param to_index: Destination square index.
    :type to_index: int
    :param cs: Current chess state.
    :type cs: chessState
    :return: ``0`` if invalid/off-board, ``1`` if empty square, ``2`` if same-color piece,
        ``3`` if opposing non-king piece, or ``4`` if opposing king.
    :rtype: int
    """
    if from_index < 0 or from_index >= 64 or cs.pieceList[from_index] is None:
        return 0
    if to_index < 0 or to_index >= 64:
        return 0
    from_white = cs.pieceList[from_index].isupper()
    target = cs.pieceList[to_index]
    if target is None:
        return 1
    if target.isupper() == from_white:
        return 2
    if target.upper() == "K":
        return 4
    return 3


def getPiecetoTextName(piece: str | None) -> str | None:
    """Convert a single-character FEN piece symbol into its human-readable English name.

    :param piece: Single-character FEN piece code (e.g., ``'P'``, ``'k'``).
    :type piece: str | None
    :return: Full descriptive piece name (e.g., ``'white pawn'``), or ``None``.
    :rtype: str | None
    """
    names = {
        "P": "white pawn",
        "B": "white bishop",
        "N": "white knight",
        "R": "white rook",
        "Q": "white queen",
        "K": "white king",
        "p": "black pawn",
        "b": "black bishop",
        "n": "black knight",
        "r": "black rook",
        "q": "black queen",
        "k": "black king",
    }
    return names.get(piece)


def getPieceTextNameOn(idx: int, cs: chessState) -> str | None:
    """Return the human-readable name of the piece on ``idx``, or ``None`` if empty.

    :param idx: Board square index (0..63).
    :type idx: int
    :param cs: Current chess state.
    :type cs: chessState
    :return: Descriptive piece name or ``None``.
    :rtype: str | None
    """
    if idx < 0 or idx >= 64 or cs.pieceList[idx] is None:
        return None
    return getPiecetoTextName(cs.pieceList[idx])


def convertLabel(label: str) -> tuple[int, int, int]:
    """Convert an algebraic square label (e.g., ``'e4'``) to ``(col, row, index)``.

    :param label: Two-character algebraic coordinate.
    :type label: str
    :return: Tuple ``(col, row, index)`` where ``index`` is in 0..63.
    :rtype: tuple[int, int, int]
    """
    col = ord(label[0].upper()) - 65
    row = 7 - (ord(label[1].upper()) - 49)
    return (col, row, row * 8 + col)


def convertIndex(index: int) -> tuple[int, int, str]:
    """Convert a 0..63 board index to ``(col, row, label)``.

    :param index: Board square index (0..63).
    :type index: int
    :return: Tuple ``(col, row, label)`` where ``label`` is uppercase algebraic (e.g., ``'E4'``).
    :rtype: tuple[int, int, str]
    """
    row = 7 - (index // 8)
    col = index % 8
    label = f"{chr(col + 65)}{chr(row + 49)}"
    return (col, row, label)


def convertColRow(col: int, row: int) -> tuple[int, str]:
    """Convert 0-based ``(col, row)`` indices to ``(index, label)``.

    :param col: File index (0..7).
    :type col: int
    :param row: Rank row index (0..7, from top rank 8 to bottom rank 1).
    :type row: int
    :return: Tuple ``(index, label)``.
    :rtype: tuple[int, str]
    """
    label = f"{chr(col + 65)}{chr((7 - row) + 49)}"
    return (row * 8 + col, label)


def isSquareAttacked(square: int, by_white: bool, cs: chessState) -> bool:
    """Determine whether ``square`` is attacked by any piece of color ``by_white``.

    Checks pawn diagonal attacks, knight jumps, king adjacency, and sliding rays
    (bishops/rooks/queens) directly without recursive move generation.

    :param square: Target square index (0..63).
    :type square: int
    :param by_white: ``True`` to test if White attacks ``square``, ``False`` for Black.
    :type by_white: bool
    :param cs: Current board state.
    :type cs: chessState
    :return: ``True`` if ``square`` is attacked by ``by_white``.
    :rtype: bool
    """
    if square < 0 or square >= 64:
        return False

    # 1. Pawn attacks: a white pawn attacks upward (so it sits one rank down-left or down-right from target)
    if by_white:
        for attacker_sq in (squareDownLeft(square), squareDownRight(square)):
            if attacker_sq < 64 and cs.pieceList[attacker_sq] == "P":
                return True
    else:
        for attacker_sq in (squareUpLeft(square), squareUpRight(square)):
            if attacker_sq < 64 and cs.pieceList[attacker_sq] == "p":
                return True

    # 2. Knight attacks
    knight_char = "N" if by_white else "n"
    knight_steps = (
        squareUp(squareUpLeft(square)),
        squareUp(squareUpRight(square)),
        squareLeft(squareUpLeft(square)),
        squareLeft(squareDownLeft(square)),
        squareDown(squareDownLeft(square)),
        squareDown(squareDownRight(square)),
        squareRight(squareUpRight(square)),
        squareRight(squareDownRight(square)),
    )
    for sq in knight_steps:
        if sq < 64 and cs.pieceList[sq] == knight_char:
            return True

    # 3. King attacks
    king_char = "K" if by_white else "k"
    king_steps = (
        squareUp(square),
        squareUpLeft(square),
        squareLeft(square),
        squareDownLeft(square),
        squareDown(square),
        squareDownRight(square),
        squareRight(square),
        squareUpRight(square),
    )
    for sq in king_steps:
        if sq < 64 and cs.pieceList[sq] == king_char:
            return True

    # 4. Orthogonal rays (Rook / Queen)
    rook_chars = ("R", "Q") if by_white else ("r", "q")
    for step_fn in (squareUp, squareDown, squareLeft, squareRight):
        curr = step_fn(square)
        while curr < 64:
            piece = cs.pieceList[curr]
            if piece is not None:
                if piece in rook_chars:
                    return True
                break
            curr = step_fn(curr)

    # 5. Diagonal rays (Bishop / Queen)
    bishop_chars = ("B", "Q") if by_white else ("b", "q")
    for step_fn in (squareUpLeft, squareUpRight, squareDownLeft, squareDownRight):
        curr = step_fn(square)
        while curr < 64:
            piece = cs.pieceList[curr]
            if piece is not None:
                if piece in bishop_chars:
                    return True
                break
            curr = step_fn(curr)

    return False


def hasKingCollision(cs: chessState) -> bool:
    """Determine whether the active player's king (``cs.turn``) is currently under attack.

    :param cs: Chess state to evaluate.
    :type cs: chessState
    :return: ``True`` if the side to move is in check.
    :rtype: bool
    """
    is_white = cs.turn == "w"
    king_char = "K" if is_white else "k"
    for idx, piece in enumerate(cs.pieceList):
        if piece == king_char:
            return isSquareAttacked(idx, not is_white, cs)
    return False


def hasInsufficientMaterial(cs: chessState) -> bool:
    """Return ``True`` if neither side has sufficient material to deliver checkmate.

    Detects K vs K, K+N vs K, K+B vs K, and K+B vs K+B on the same square color.

    :param cs: Board state to inspect.
    :type cs: chessState
    :return: ``True`` if position is a dead draw by insufficient material.
    :rtype: bool
    """
    non_kings = [(idx, p) for idx, p in enumerate(cs.pieceList) if p is not None and p.upper() != "K"]
    if not non_kings:
        return True
    if len(non_kings) == 1:
        _, piece = non_kings[0]
        if piece.upper() in ("N", "B"):
            return True
    if len(non_kings) == 2:
        (idx1, p1), (idx2, p2) = non_kings
        if p1.upper() == "B" and p2.upper() == "B" and (p1.isupper() != p2.isupper()):
            color1 = (idx1 // 8 + idx1 % 8) % 2
            color2 = (idx2 // 8 + idx2 % 8) % 2
            if color1 == color2:
                return True
    return False


def isFiftyMoveRule(cs: chessState) -> bool:
    """Return ``True`` if the 50-move rule (100 half-moves without pawn advance or capture) is reached.

    :param cs: Board state to inspect.
    :type cs: chessState
    :return: ``True`` if ``cs.half_move >= 100``.
    :rtype: bool
    """
    return cs.half_move >= 100


def isThreefoldRepetition(cs: chessState, history: list[chessState] | None = None) -> bool:
    """Return ``True`` if ``cs`` has occurred at least three times in ``history``.

    Compares the 4-field position key (board, turn, castling rights, and en passant target).
    If ``history`` already ends with ``cs``, counts occurrences across ``history`` directly;
    otherwise includes ``cs`` as an additional occurrence.

    :param cs: Current board state to test.
    :type cs: chessState
    :param history: Chronological sequence of board states in the game.
    :type history: list[chessState] | None
    :return: ``True`` if the position has been repeated at least three times.
    :rtype: bool
    """
    if not history:
        return False
    target_key = cs.getPositionKey()
    count = sum(1 for state in history if state.getPositionKey() == target_key)
    if history[-1] != cs:
        count += 1
    return count >= 3


def isGameOver(cs: chessState, history: list[chessState] | None = None) -> int:
    """Check whether the current position is checkmate, stalemate/draw, or ongoing.

    Evaluates checkmate/stalemate first, then checks the 50-move inaction rule,
    threefold repetition, and insufficient material.

    :param cs: Chess state to evaluate for the side to move.
    :type cs: chessState
    :param history: Optional list of historical states for threefold repetition detection.
    :type history: list[chessState] | None
    :return: ``0`` if legal moves exist and no draw rule is triggered, ``1`` for checkmate,
        or ``2`` for stalemate/draw.
    :rtype: int
    """
    is_white = cs.turn == "w"
    has_legal_move = False
    for idx, piece in enumerate(cs.pieceList):
        if piece is not None and (piece.isupper() == is_white):
            moves = getMovesFromSquare(idx, cs, True)
            if len(moves) > 0:
                has_legal_move = True
                break

    if not has_legal_move:
        if hasKingCollision(cs):
            return 1
        return 2

    if isFiftyMoveRule(cs) or isThreefoldRepetition(cs, history) or hasInsufficientMaterial(cs):
        return 2

    return 0


def getAllLegalMoves(cs: chessState) -> list[chessMove]:
    """Return all legal moves available for the active player in ``cs``.

    :param cs: Current board state.
    :type cs: chessState
    :return: List of all legal :class:`chessMove` objects.
    :rtype: list[chessMove]
    """
    is_white = cs.turn == "w"
    moves: list[chessMove] = []
    for idx, piece in enumerate(cs.pieceList):
        if piece is not None and (piece.isupper() == is_white):
            moves.extend(getMovesFromSquare(idx, cs, True))
    return moves


def movePiece(move: chessMove, cs: chessState, filterForCheck: bool = True):
    """Apply a move to the given :class:`chessState.chessState` in place and advance the turn.

    Updates piece locations, castling rooks, pawn promotions, en passant targets/captures,
    half-move clock, full-move counter, and castling rights.

    :param move: Move to execute.
    :type move: chessMove
    :param cs: Board state to mutate.
    :type cs: chessState
    :param filterForCheck: Unused flag retained for API compatibility.
    :type filterForCheck: bool
    """
    moving_piece = cs.pieceList[move.start]
    target_piece = cs.pieceList[move.end]
    is_capture = move.is_capture or (target_piece is not None)

    was_white_castle = False
    was_black_castle = False
    if move.promotionPiece == "":
        if len(move.castleRookSquares) == 0:
            cs.pieceList[move.end] = moving_piece
        else:
            cs.pieceList[move.end] = moving_piece
            cs.pieceList[move.castleRookSquares[1]] = cs.pieceList[move.castleRookSquares[0]]
            cs.pieceList[move.castleRookSquares[0]] = None
            if cs.turn == "w":
                was_white_castle = True
            else:
                was_black_castle = True
    else:
        cs.pieceList[move.end] = move.promotionPiece
        cs.half_move = 0

    cs.pieceList[move.start] = None
    cs.toggle_turn()

    if moving_piece is not None and moving_piece.upper() == "P":
        cs.half_move = 0
        if move.enpassantFlag and not is_capture:
            if moving_piece == "p":
                _, _, label = convertIndex(squareUp(move.end))
                cs.enpassant_targets = label
            else:
                _, _, label = convertIndex(squareDown(move.end))
                cs.enpassant_targets = label
        elif move.enpassantFlag and is_capture:
            if moving_piece == "p":
                cs.pieceList[squareUp(move.end)] = None
            else:
                cs.pieceList[squareDown(move.end)] = None
            cs.enpassant_targets = "-"
        else:
            cs.enpassant_targets = "-"
    else:
        if is_capture or move.promotionPiece != "":
            cs.half_move = 0
        else:
            cs.half_move += 1
        cs.enpassant_targets = "-"

    # Update castling rights when kings or rooks move
    if cs.pieceList[move.end] == "K" or was_white_castle or move.start == 60:
        cs.castle_white_king = False
        cs.castle_white_queen = False
    elif move.start == 56:
        cs.castle_white_queen = False
    elif move.start == 63:
        cs.castle_white_king = False

    if cs.pieceList[move.end] == "k" or was_black_castle or move.start == 4:
        cs.castle_black_king = False
        cs.castle_black_queen = False
    elif move.start == 0:
        cs.castle_black_queen = False
    elif move.start == 7:
        cs.castle_black_king = False

    # Revoke castling rights if a rook's starting square is captured
    if move.end == 56:
        cs.castle_white_queen = False
    elif move.end == 63:
        cs.castle_white_king = False
    elif move.end == 0:
        cs.castle_black_queen = False
    elif move.end == 7:
        cs.castle_black_king = False


def filterCheckResolve(moveList: list[chessMove], cs: chessState) -> list[chessMove]:
    """Filter out candidate moves that leave the moving player's own king in check.

    Also removes pseudo-moves that capture the opposing king directly.

    :param moveList: Candidate moves to test.
    :type moveList: list[chessMove]
    :param cs: Current board state prior to the move.
    :type cs: chessState
    :return: Subset of ``moveList`` that are legal.
    :rtype: list[chessMove]
    """
    filteredResults: list[chessMove] = []
    for move in moveList:
        if cs.pieceList[move.end] is not None and cs.pieceList[move.end].upper() == "K":
            continue
        pretendGame = cs.copy()
        movePiece(move, pretendGame, False)
        pretendGame.toggle_turn()
        if not hasKingCollision(pretendGame):
            filteredResults.append(move)
    return filteredResults


def getPawnMoves(startIndex: int, cs: chessState, filterForCheck: bool = True) -> list[chessMove]:
    """Generate candidate or legal moves for a pawn at ``startIndex``.

    :param startIndex: Square index of the pawn (0..63).
    :type startIndex: int
    :param cs: Current board state.
    :type cs: chessState
    :param filterForCheck: When ``True``, filters out moves that leave own king in check.
    :type filterForCheck: bool
    :return: List of pawn moves.
    :rtype: list[chessMove]
    """
    result: list[chessMove] = []
    is_white = cs.pieceList[startIndex].isupper()

    if is_white:
        advanceMove = squareUp
        advanceLeftMove = squareUpLeft
        advanceRightMove = squareUpRight
        initialRow = 1
    else:
        advanceMove = squareDown
        advanceLeftMove = squareDownLeft
        advanceRightMove = squareDownRight
        initialRow = 6

    def considerPromotion(s_idx: int, e_idx: int, is_capture: bool = False) -> list[chessMove]:
        promos: list[chessMove] = []
        _, endRow, _ = convertIndex(e_idx)
        if is_white and endRow == 7:
            for p in ("Q", "R", "B", "N"):
                promos.append(chessMove(s_idx, e_idx, is_capture=is_capture, promotionPiece=p))
        elif (not is_white) and endRow == 0:
            for p in ("q", "r", "b", "n"):
                promos.append(chessMove(s_idx, e_idx, is_capture=is_capture, promotionPiece=p))
        return promos

    def considerDiagonal(s_idx: int, step_fn) -> list[chessMove]:
        diag_moves: list[chessMove] = []
        e_idx = step_fn(s_idx)
        if e_idx >= 64:
            return diag_moves
        _, _, label = convertIndex(e_idx)
        is_ep = False
        if label == cs.enpassant_targets.upper() and cs.enpassant_targets != "-":
            ep_pawn_sq = squareDown(e_idx) if is_white else squareUp(e_idx)
            expected_enemy_pawn = "p" if is_white else "P"
            if ep_pawn_sq < 64 and cs.pieceList[ep_pawn_sq] == expected_enemy_pawn:
                collisionType = 3
                is_ep = True
            else:
                collisionType = getCollisionType(s_idx, e_idx, cs)
        else:
            collisionType = getCollisionType(s_idx, e_idx, cs)

        if collisionType == 3:
            promos = considerPromotion(s_idx, e_idx, is_capture=True)
            if promos:
                diag_moves.extend(promos)
            else:
                diag_moves.append(chessMove(s_idx, e_idx, is_capture=True, enpassantFlag=is_ep))
        elif collisionType == 4:
            diag_moves.append(chessMove(s_idx, e_idx, is_check=True))
        return diag_moves

    _, startRow, _ = convertIndex(startIndex)

    # Single step forward
    endIndex = advanceMove(startIndex)
    collisionType = getCollisionType(startIndex, endIndex, cs)
    fwdIdx = 64
    if collisionType == 1:
        promos = considerPromotion(startIndex, endIndex, is_capture=False)
        if promos:
            result.extend(promos)
        else:
            result.append(chessMove(startIndex, endIndex))
        fwdIdx = endIndex

    # Double step forward from starting rank
    if startRow == initialRow and fwdIdx != 64:
        endIndex2 = advanceMove(fwdIdx)
        if getCollisionType(startIndex, endIndex2, cs) == 1:
            result.append(chessMove(startIndex, endIndex2, enpassantFlag=True))

    # Captures
    result.extend(considerDiagonal(startIndex, advanceLeftMove))
    result.extend(considerDiagonal(startIndex, advanceRightMove))

    if filterForCheck:
        return filterCheckResolve(result, cs)
    return result


def getKnightMoves(startIndex: int, cs: chessState, filterForCheck: bool = True) -> list[chessMove]:
    """Generate candidate or legal moves for a knight at ``startIndex``.

    :param startIndex: Square index of the knight (0..63).
    :type startIndex: int
    :param cs: Current board state.
    :type cs: chessState
    :param filterForCheck: When ``True``, filters out moves that leave own king in check.
    :type filterForCheck: bool
    :return: List of knight moves.
    :rtype: list[chessMove]
    """
    result: list[chessMove] = []
    steps = (
        lambda x: squareUp(squareUpLeft(x)),
        lambda x: squareUp(squareUpRight(x)),
        lambda x: squareLeft(squareUpLeft(x)),
        lambda x: squareLeft(squareDownLeft(x)),
        lambda x: squareDown(squareDownLeft(x)),
        lambda x: squareDown(squareDownRight(x)),
        lambda x: squareRight(squareUpRight(x)),
        lambda x: squareRight(squareDownRight(x)),
    )
    for move_lambda in steps:
        endIndex = move_lambda(startIndex)
        collisionType = getCollisionType(startIndex, endIndex, cs)
        if collisionType == 1:
            result.append(chessMove(startIndex, endIndex))
        elif collisionType == 3:
            result.append(chessMove(startIndex, endIndex, is_capture=True))
        elif collisionType == 4:
            result.append(chessMove(startIndex, endIndex, is_check=True))

    if filterForCheck:
        return filterCheckResolve(result, cs)
    return result


def considerBishopRookQueenMove(move_lambda, startIndex: int, cs: chessState, result: list[chessMove]):
    """Slide along a ray defined by ``move_lambda`` and append reachable moves to ``result``.

    :param move_lambda: Step function taking a square index and returning the next square index.
    :type move_lambda: collections.abc.Callable[[int], int]
    :param startIndex: Origin square index (0..63).
    :type startIndex: int
    :param cs: Current board state.
    :type cs: chessState
    :param result: Mutable list of :class:`chessMove` objects to append to.
    :type result: list[chessMove]
    """
    a = startIndex
    while True:
        b = move_lambda(a)
        collisionType = getCollisionType(startIndex, b, cs)
        if collisionType == 0 or collisionType == 2:
            return
        if collisionType == 1:
            result.append(chessMove(startIndex, b))
            a = b
        elif collisionType == 3:
            result.append(chessMove(startIndex, b, is_capture=True))
            return
        elif collisionType == 4:
            result.append(chessMove(startIndex, b, is_check=True))
            return


def getBishopMoves(startIndex: int, cs: chessState, filterForCheck: bool = True) -> list[chessMove]:
    """Generate candidate or legal moves for a bishop at ``startIndex``.

    :param startIndex: Square index of the bishop (0..63).
    :type startIndex: int
    :param cs: Current board state.
    :type cs: chessState
    :param filterForCheck: When ``True``, filters out moves that leave own king in check.
    :type filterForCheck: bool
    :return: List of bishop moves.
    :rtype: list[chessMove]
    """
    result: list[chessMove] = []
    for ray in (squareUpLeft, squareDownLeft, squareUpRight, squareDownRight):
        considerBishopRookQueenMove(ray, startIndex, cs, result)
    if filterForCheck:
        return filterCheckResolve(result, cs)
    return result


def getRookMoves(startIndex: int, cs: chessState, filterForCheck: bool = True) -> list[chessMove]:
    """Generate candidate or legal moves for a rook at ``startIndex``.

    :param startIndex: Square index of the rook (0..63).
    :type startIndex: int
    :param cs: Current board state.
    :type cs: chessState
    :param filterForCheck: When ``True``, filters out moves that leave own king in check.
    :type filterForCheck: bool
    :return: List of rook moves.
    :rtype: list[chessMove]
    """
    result: list[chessMove] = []
    for ray in (squareUp, squareDown, squareRight, squareLeft):
        considerBishopRookQueenMove(ray, startIndex, cs, result)
    if filterForCheck:
        return filterCheckResolve(result, cs)
    return result


def getQueenMoves(startIndex: int, cs: chessState, filterForCheck: bool = True) -> list[chessMove]:
    """Generate candidate or legal moves for a queen at ``startIndex``.

    :param startIndex: Square index of the queen (0..63).
    :type startIndex: int
    :param cs: Current board state.
    :type cs: chessState
    :param filterForCheck: When ``True``, filters out moves that leave own king in check.
    :type filterForCheck: bool
    :return: List of queen moves.
    :rtype: list[chessMove]
    """
    result: list[chessMove] = []
    result.extend(getBishopMoves(startIndex, cs, False))
    result.extend(getRookMoves(startIndex, cs, False))
    if filterForCheck:
        return filterCheckResolve(result, cs)
    return result


def getKingMoves(startIndex: int, cs: chessState) -> list[chessMove]:
    """Generate legal moves (including castling) for a king at ``startIndex``.

    :param startIndex: Square index of the king (0..63).
    :type startIndex: int
    :param cs: Current board state.
    :type cs: chessState
    :return: List of legal king moves.
    :rtype: list[chessMove]
    """
    is_white = cs.pieceList[startIndex].isupper()
    result: list[chessMove] = []

    for step_fn in (
        squareUp,
        squareUpLeft,
        squareLeft,
        squareDownLeft,
        squareDown,
        squareDownRight,
        squareRight,
        squareUpRight,
    ):
        endIndex = step_fn(startIndex)
        collisionType = getCollisionType(startIndex, endIndex, cs)
        if collisionType == 1:
            candidate = chessMove(startIndex, endIndex)
        elif collisionType == 3:
            candidate = chessMove(startIndex, endIndex, is_capture=True)
        else:
            continue
        pretendGame = cs.copy()
        movePiece(candidate, pretendGame, False)
        pretendGame.toggle_turn()
        if not hasKingCollision(pretendGame):
            result.append(candidate)

    # Kingside castling
    if not isSquareAttacked(startIndex, not is_white, cs):
        if is_white and cs.castle_white_king and startIndex == 60 and cs.pieceList[63] == "R":
            if cs.pieceList[61] is None and cs.pieceList[62] is None:
                if not isSquareAttacked(61, False, cs) and not isSquareAttacked(62, False, cs):
                    result.append(chessMove(60, 62, castleRookSquares=[63, 61]))
        elif (not is_white) and cs.castle_black_king and startIndex == 4 and cs.pieceList[7] == "r":
            if cs.pieceList[5] is None and cs.pieceList[6] is None:
                if not isSquareAttacked(5, True, cs) and not isSquareAttacked(6, True, cs):
                    result.append(chessMove(4, 6, castleRookSquares=[7, 5]))

        # Queenside castling
        if is_white and cs.castle_white_queen and startIndex == 60 and cs.pieceList[56] == "R":
            if cs.pieceList[59] is None and cs.pieceList[58] is None and cs.pieceList[57] is None:
                if not isSquareAttacked(59, False, cs) and not isSquareAttacked(58, False, cs):
                    result.append(chessMove(60, 58, castleRookSquares=[56, 59]))
        elif (not is_white) and cs.castle_black_queen and startIndex == 4 and cs.pieceList[0] == "r":
            if cs.pieceList[3] is None and cs.pieceList[2] is None and cs.pieceList[1] is None:
                if not isSquareAttacked(3, True, cs) and not isSquareAttacked(2, True, cs):
                    result.append(chessMove(4, 2, castleRookSquares=[0, 3]))

    return result


def getMovesFromSquare(start: int, cs: chessState, filterForCheck: bool = True) -> list[chessMove]:
    """Return all valid moves originating from the ``start`` square.

    :param start: Origin square index (0..63).
    :type start: int
    :param cs: Current chess state.
    :type cs: chessState
    :param filterForCheck: Whether to filter out moves leaving the moving side in check.
    :type filterForCheck: bool
    :return: List of :class:`chessMove` objects available from ``start``.
    :rtype: list[chessMove]
    """
    if start < 0 or start >= 64 or cs.pieceList[start] is None:
        return []
    piece = cs.pieceList[start].upper()
    if piece == "P":
        return getPawnMoves(start, cs, filterForCheck)
    if piece == "N":
        return getKnightMoves(start, cs, filterForCheck)
    if piece == "B":
        return getBishopMoves(start, cs, filterForCheck)
    if piece == "R":
        return getRookMoves(start, cs, filterForCheck)
    if piece == "Q":
        return getQueenMoves(start, cs, filterForCheck)
    if piece == "K":
        return getKingMoves(start, cs)
    return []
