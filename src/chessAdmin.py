"""Core chess rules, move generation, check filtering, and game-over evaluation."""

from chessState import chessState, player_t
import copy


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
    :ivar is_check: Whether the move directly attacks the opposing king.
    :vartype is_check: bool
    :ivar promotionPiece: FEN character of the promoted piece, or ``''`` if not a promotion.
    :vartype promotionPiece: str
    :ivar castleRookSquares: Two-element list ``[rook_start, rook_end]`` for castling moves.
    :vartype castleRookSquares: list[int]
    """

    def __init__(self, start : int, end : int, is_capture = False, promotionPiece = "", enpassantFlag = False, is_check = False, castleRookSquares = []):
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
        :param is_check: True if the move targets the opponent's king.
        :type is_check: bool
        :param castleRookSquares: Rook ``[from_idx, to_idx]`` squares when castling.
        :type castleRookSquares: list[int]
        """
        self.start = start
        self.end = end
        self.is_capture = is_capture
        self.enpassantFlag= enpassantFlag
        self.is_check = is_check
        self.promotionPiece = promotionPiece
        self.castleRookSquares = castleRookSquares


# Gets the square index moving from rank A -> H. 
# Return 64 if off the board
def squareUp(idx : int):
    """Return the square index one rank up (towards rank 8), or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    if((idx <= 7) or (idx >= 64)):
        return 64
    return idx - 8        


# Gets the square index moving from rank H -> A. 
# Return 64 if off the board
def squareDown(idx : int):
    """Return the square index one rank down (towards rank 1), or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    if(idx >=56):
        return 64
    return idx + 8


# Gets the square index moving from file 8 -> 1. 
# Return 64 if off the board
def squareLeft(idx : int):
    """Return the square index one file left (towards file A), or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    if(idx % 8 == 0):
        return 64
    return idx - 1


# Gets the square index moving from file 1 -> 8. 
# Return 64 if off the board
def squareRight(idx : int):
    """Return the square index one file right (towards file H), or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    if(idx % 8 == 7):
        return 64
    return idx + 1


# Gets the square index moving up then right
# Return 64 if off the board
def squareUpRight(idx : int):
    """Return the square index one step diagonally up-right, or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    val = squareRight(idx)
    if(val >= 64):
        return val
    return squareUp(val)


# Gets the square index moving up then left
# Return 64 if off the board
def squareUpLeft(idx : int):
    """Return the square index one step diagonally up-left, or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    val = squareLeft(idx)
    if(val >= 64):
        return val
    return squareUp(val)        


# Gets the square index moving down then right
# Return 64 if off the board
def squareDownRight(idx : int):
    """Return the square index one step diagonally down-right, or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    val = squareRight(idx)
    if(val >= 64):
        return val
    return squareDown(val)


# Gets the square index moving down then left
# Return 64 if off the board
def squareDownLeft(idx : int):
    """Return the square index one step diagonally down-left, or 64 if off the board.

    :param idx: Starting square index (0..63).
    :type idx: int
    :return: Target square index, or 64 if out of bounds.
    :rtype: int
    """
    val = squareLeft(idx)
    if(val >= 64):
        return val
    return squareDown(val)        


# For a move with given color piece_sprite
# returns "0" if move is off the board, or invalid
# returns "1" if a normal move without collision
# returns '2' if a collision with a same color
# returns "3" if move collides with opposite color 
# returns "4" if move collides with opposite king
def getCollisionType(from_index : int, to_index : int, cs : chessState):
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
    if(cs.pieceList[from_index] == None):
        return 0
    if(to_index >= 64):
        return 0
    from_white = cs.pieceList[from_index].isupper()
    if(cs.pieceList[to_index] == None):
        return 1
    if(cs.pieceList[to_index].isupper() == from_white):
        return 2
    if(cs.pieceList[to_index].upper() == "K"):
        return 4
    else:
        return 3


# Get piece text name
def getPiecetoTextName(piece):
    """Convert a single-character FEN piece symbol into its human-readable English name.

    :param piece: Single-character FEN piece code (e.g., ``'P'``, ``'k'``).
    :type piece: str
    :return: Full descriptive piece name (e.g., ``'white pawn'``), or ``None``.
    :rtype: str | None
    """
    match piece:
        case "P":
            return "white pawn"
        case "B":
            return "white bishop"
        case "N":
            return "white knight"
        case "R":
            return "white rook"
        case "Q":
            return "white queen"
        case "K":
            return "white king"  
        case "p":
            return "black pawn"
        case "b":
            return "black bishop"
        case "n":
            return "black knight"
        case "r":
            return "black rook"
        case "q":
            return "black queen"
        case "k":
            return "black king"                                                                        
        case _:
            None


# Get text name on square
def getPieceTextNameOn(idx, cs : chessState):
    """Return the human-readable name of the piece on ``idx``, or ``None`` if empty.

    :param idx: Board square index (0..63).
    :type idx: int
    :param cs: Current chess state.
    :type cs: chessState
    :return: Descriptive piece name or ``None``.
    :rtype: str | None
    """
    if(cs.pieceList[idx] == None):
        return None
    return getPiecetoTextName(cs.pieceList[idx])


# Takes a square label and returns the (col,row,index)
def convertLabel(label : str):
    """Convert an algebraic square label (e.g., ``'e4'``) to ``(col, row, index)``.

    :param label: Two-character algebraic coordinate.
    :type label: str
    :return: Tuple ``(col, row, index)`` where ``index`` is in 0..63.
    :rtype: tuple[int, int, int]
    """
    col = ord(label[0].upper())-65
    row = 7-(ord(label[1].upper())-49) # One indexed
    return (col,row,row*8 + col)


# Index to (col,row, label)
def convertIndex(index : int):
    """Convert a 0..63 board index to ``(col, row, label)``.

    :param index: Board square index (0..63).
    :type index: int
    :return: Tuple ``(col, row, label)`` where ``label`` is uppercase algebraic (e.g., ``'E4'``).
    :rtype: tuple[int, int, str]
    """
    row = 7-(index // 8)
    col = index % 8
    label = f"{chr(col+65)}{chr(row+48+1)}" # One indexed
    return (col,row,label)


# Index to (index, label)
def convertColRow(col : int, row : int):
    """Convert 0-based ``(col, row)`` indices to ``(index, label)``.

    :param col: File index (0..7).
    :type col: int
    :param row: Rank row index (0..7, from top rank 8 to bottom rank 1).
    :type row: int
    :return: Tuple ``(index, label)``.
    :rtype: tuple[int, str]
    """
    label = f"{chr(col+65)}{chr((7-row)+48+1)}" # One indexed
    return (row*8+col,label)


# Evaluates whether the given chessState has king collision
# True = the cs.turn king is under check form the !cs.turn
def hasKingCollision(cs : chessState):
    """Determine whether the active player's king (``cs.turn``) is currently under attack.

    :param cs: Chess state to evaluate.
    :type cs: chessState
    :return: ``True`` if the side to move is in check or adjacent to the enemy king.
    :rtype: bool
    """
    is_white = (cs.turn == 'w')
    for idx,piece in enumerate(cs.pieceList):
        # If opposite color 
        if (piece != None) and (piece.isupper() != is_white):
            if(piece.upper() == "K"): # Avoid kissing kings by looking for collisions with other king
                # For surrounding indexes
                for i in [squareUp(idx),squareUpLeft(idx),squareLeft(idx),squareDownLeft(idx),squareDown(idx),squareDownRight(idx),squareRight(idx),squareUpRight(idx)]:
                    # Out of bounds
                    if(i == 64):
                        continue
                    # Look for contact with other king
                    p = cs.pieceList[i]
                    if(p != None) and (p.upper() == "K"):
                        return True   # Collision                
            else:  # If not a king, can make call to get moves and look for check
                moves = getMovesFromSquare(idx,cs,False)
                for m in moves:
                    if(m.is_check):
                        return True # Collision

    return False


# Look for 0 = not over, 1 = checkmate, 2 = stalemate
def isGameOver(cs : chessState):
    """Check whether the current position is checkmate, stalemate, or ongoing.

    :param cs: Chess state to evaluate for the side to move.
    :type cs: chessState
    :return: ``0`` if legal moves exist, ``1`` for checkmate, or ``2`` for stalemate.
    :rtype: int
    """
    # If at least one move is possible
    is_white = (cs.turn == 'w')
    for idx,piece in enumerate(cs.pieceList):
        # If opposite color and not a king
        if (piece != None) and (piece.isupper() == is_white):
            moves = getMovesFromSquare(idx,cs,True)
            if(len(moves) > 0):
                return 0
    # Now look for stalemate
    if(hasKingCollision(cs)):
        return 1 # Checkmate
    else:
        return 2 # Stalemate


# Moves a piece and toggles the turn
def movePiece(move : chessMove, cs : chessState, filterForCheck = True):
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
    # Is a promotion, or normal / castle move
    was_white_castle = False
    was_black_castle = False
    if(move.promotionPiece == ""):
        if(len(move.castleRookSquares) == 0):
            # Normal move
            cs.pieceList[move.end] = cs.pieceList[move.start]
        else:
            # Castle move
            cs.pieceList[move.end] = cs.pieceList[move.start]
            cs.pieceList[move.castleRookSquares[1]] = cs.pieceList[move.castleRookSquares[0]]
            cs.pieceList[move.castleRookSquares[0]] = None
            if(cs.turn == "w"):
                was_white_castle = True
            else:
                was_black_castle = True
    else:
        # Promotion
        cs.pieceList[move.end] = move.promotionPiece
        # Half move is 0
        cs.half_move = 0

    # Remove start
    cs.pieceList[move.start] = None
    # Toggle a turn
    cs.toggle_turn()
    # Half moves for pawn
    if(cs.pieceList[move.end].upper() == "P"):
        cs.half_move = 0
        # This initiate enpassant
        if(move.enpassantFlag and (not move.is_capture)):
            if(cs.pieceList[move.end] == 'p'):
                (col,row,label) = convertIndex(squareUp(move.end))
                cs.enpassant_targets = label
            else:
                (col,row,label) = convertIndex(squareDown(move.end))
                cs.enpassant_targets = label
        elif(move.enpassantFlag and (move.is_capture)): # This is an en passant capture
            if(cs.pieceList[move.end] == 'p'):
                cs.pieceList[squareUp(move.end)] = None
            else:
                cs.pieceList[squareDown(move.end)] = None
            cs.enpassant_targets = "-"
        else: # Regular pawn move
            cs.enpassant_targets = "-"
    else:
        cs.half_move += 1
        # Default get rid of enpassant
        cs.enpassant_targets = "-"
   
    # Toggle castle flags if necessary
    if(cs.pieceList[move.end] == "K") or was_white_castle:
        cs.castle_white_king = False
        cs.castle_white_queen = False
    elif(cs.pieceList[move.end] == "R"):
        if(move.start == 56):
            cs.castle_white_queen = False
        elif(move.start == 63):
            cs.castle_white_king = False

    elif(cs.pieceList[move.end] == "k") or was_black_castle:
        cs.castle_black_king = False
        cs.castle_black_queen = False
    elif(cs.pieceList[move.end] == "r"):
        if(move.start == 0):
            cs.castle_black_queen = False
        elif(move.start == 7):
            cs.castle_black_king = False


# Looks for check after a move is made
def filterCheckResolve(moveList : list, cs : chessState):
    """Filter out candidate moves that leave the moving player's own king in check.

    :param moveList: Candidate moves to test.
    :type moveList: list[chessMove]
    :param cs: Current board state prior to the move.
    :type cs: chessState
    :return: Subset of ``moveList`` that does not leave the player in check.
    :rtype: list[chessMove]
    """
    filteredResults = []
    for move in moveList:
        pretendGame = copy.deepcopy(cs)
        movePiece(move,pretendGame,False)
        pretendGame.toggle_turn()
        in_check = hasKingCollision(pretendGame)
        if(not in_check):
            filteredResults.append(move)
    return filteredResults


# Moves for a pawn.  Returns a list of chessMove (or empty list)
def getPawnMoves(startIndex : int, cs : chessState, filterForCheck = True):
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
    result = []

    if(cs.pieceList[startIndex].isupper()):
        advanceMove = squareUp
        advanceLeftMove = squareUpLeft
        advanceRightMove = squareUpRight
        initialRow = 1
    else:
        advanceMove = squareDown
        advanceLeftMove = squareDownLeft
        advanceRightMove = squareDownRight
        initialRow = 6

    def considerPromotion (startIndex : int, endIndex : int, cs : chessState):
        result = []
        (endCol,endRow,endLabel) = convertIndex(endIndex)
        if(cs.pieceList[startIndex].isupper()):
            if(endRow == 7):
                result.append(chessMove(startIndex,endIndex,promotionPiece="Q"))
                result.append(chessMove(startIndex,endIndex,promotionPiece="R"))
                result.append(chessMove(startIndex,endIndex,promotionPiece="B"))
                result.append(chessMove(startIndex,endIndex,promotionPiece="N"))
        else:
            if(endRow == 0):
                result.append(chessMove(startIndex,endIndex,promotionPiece="q"))
                result.append(chessMove(startIndex,endIndex,promotionPiece="r"))
                result.append(chessMove(startIndex,endIndex,promotionPiece="b"))
                result.append(chessMove(startIndex,endIndex,promotionPiece="n"))     
        return result       

    def considerDiagonal(startIndex : int, cs : chessState, move):
        result = []
        endIndex = move(startIndex)
        (col,row,label) = convertIndex(endIndex)
        is_enpassant_flag = False
        if(label == cs.enpassant_targets):
            collisionType = 3
            is_enpassant_flag = True
        else:
            collisionType = getCollisionType(startIndex,endIndex,cs)
        fwdIdex = 64
        match collisionType:
            case 0: # Invalid
                None
            case 1: # Normal
                None
            case 2: # Same color
                None
            case 3: # Opposite color
                # Move
                result.append(chessMove(startIndex,endIndex,is_capture=True,enpassantFlag=is_enpassant_flag))
                # Handle promotion if necessary
                result.extend(considerPromotion(startIndex,endIndex,cs))
            case 4: # Opposite King
                result.append(chessMove(startIndex,endIndex,is_check=True))
        return result

    (startCol,startRow,startLabel) = convertIndex(startIndex)

    # Forward advance
    endIndex = advanceMove(startIndex)
    collisionType = getCollisionType(startIndex,endIndex,cs)
    fwdIdex = 64
    match collisionType:
        case 0: # Invalid
            None
        case 1: # Normal
            # Move Forward
            result.append(chessMove(startIndex,endIndex))
            # Handle promotion if necessary
            result.extend(considerPromotion(startIndex,endIndex,cs))
            fwdIdex = endIndex # Mark this forward
        case 2: # Same color
            None
        case 3: # Opposite color
            None
        case 4: # Opposite King
            None

    # Second forward advance
    if(startRow == initialRow) and (fwdIdex != 64):
        endIndex = advanceMove(fwdIdex) # Move twice from fwdIdx
        collisionType = getCollisionType(startIndex,endIndex,cs)
        match collisionType:
            case 0: # Invalid
                None
            case 1: # Normal
                # Move forward, mark en passant
                result.append(chessMove(startIndex,endIndex,enpassantFlag=True))
            case 2: # Same color
                None
            case 3: # Opposite color
                None
            case 4: # Opposite King
                None

    # Look at normal captures
        
    # Forward Left advance
    result.extend(considerDiagonal(startIndex,cs,advanceLeftMove))
    # Forward Right advance
    result.extend(considerDiagonal(startIndex,cs,advanceRightMove))

    # Guard against recursion
    if(filterForCheck):
        # If in check, filter moves that don't resolve it
        return filterCheckResolve(result,cs)
    else:
        return result


# Moves for a knight.  Returns a list of chessMove (or empty list)
def getKnightMoves(startIndex : int, cs : chessState, filterForCheck = True):
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

    # Shared code for a knight move
    def considerKnightMove(move_lambda,startIndex : int, cs : chessState, result : list):
        endIndex = move_lambda(startIndex)
        collisionType = getCollisionType(startIndex,endIndex,cs)
        match collisionType:
            case 0: # Invalid
                None
            case 1: # Normal
                # Move
                result.append(chessMove(startIndex,endIndex))
            case 2: # Same color
                None
            case 3: # Opposite color
                result.append(chessMove(startIndex,endIndex,is_capture=True))
            case 4: # Opposite King
                result.append(chessMove(startIndex,endIndex,is_check=True))

    result = []
    considerKnightMove(lambda x:squareUp(squareUpLeft(x)),startIndex,cs,result)
    
    considerKnightMove(lambda x:squareUp(squareUpRight(x)),startIndex,cs,result)
    considerKnightMove(lambda x:squareLeft(squareUpLeft(x)),startIndex,cs,result)
    considerKnightMove(lambda x:squareLeft(squareDownLeft(x)),startIndex,cs,result)
    considerKnightMove(lambda x:squareDown(squareDownLeft(x)),startIndex,cs,result)
    considerKnightMove(lambda x:squareDown(squareDownRight(x)),startIndex,cs,result)
    considerKnightMove(lambda x:squareRight(squareUpRight(x)),startIndex,cs,result)
    considerKnightMove(lambda x:squareRight(squareDownRight(x)),startIndex,cs,result)

    # Guard against recursion
    if(filterForCheck):
        # If in check, filter moves that don't resolve it
        return filterCheckResolve(result,cs)
    else:
        return result


# Shared code for moves until stop for bishops, rooks, queens
def considerBishopRookQueenMove(move_lambda,startIndex : int, cs : chessState, result : list):
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
    b = a
    while(True):
        b = move_lambda(a)
        collisionType = getCollisionType(startIndex,b,cs)
        match collisionType:
            case 0: # Invalid
                return 
            case 1: # Normal
                # Move
                result.append(chessMove(startIndex,b))
                # Keep going
                a = b
            case 2: # Same color
                return 
            case 3: # Opposite color
                result.append(chessMove(startIndex,b,is_capture=True))
                return 
            case 4: # Opposite King
                result.append(chessMove(startIndex,b,is_check=True))
                return 


# Moves for a bishop.  Returns a list of chessMove (or empty list)
def getBishopMoves(startIndex : int, cs : chessState, filterForCheck = True):
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
    result = []
    considerBishopRookQueenMove(squareUpLeft,startIndex,cs,result)
    considerBishopRookQueenMove(squareDownLeft,startIndex,cs,result)
    considerBishopRookQueenMove(squareUpRight,startIndex,cs,result)
    considerBishopRookQueenMove(squareDownRight,startIndex,cs,result)
    # Guard against recursion
    if(filterForCheck):
        # If in check, filter moves that don't resolve it
        return filterCheckResolve(result,cs)
    else:
        return result


# Moves for a rook.  Returns a list of chessMove (or empty list)
def getRookMoves(startIndex : int, cs : chessState, filterForCheck = True):
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
    result = []
    considerBishopRookQueenMove(squareUp,startIndex,cs,result)
    considerBishopRookQueenMove(squareDown,startIndex,cs,result)
    considerBishopRookQueenMove(squareRight,startIndex,cs,result)
    considerBishopRookQueenMove(squareLeft,startIndex,cs,result)
    # If in check, filter moves that don't resolve it
    # Guard against recursion
    if(filterForCheck):
        # If in check, filter moves that don't resolve it
        return filterCheckResolve(result,cs)
    else:
        return result


# Moves for a queen.  Returns a list of chessMove (or empty list)
def getQueenMoves(startIndex : int, cs : chessState, filterForCheck = True):
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
    result = []
    result.extend(getBishopMoves(startIndex,cs,filterForCheck))
    result.extend(getRookMoves(startIndex,cs,filterForCheck))
    # If in check, filter moves that don't resolve it
    # Guard against recursion
    if(filterForCheck):
        # If in check, filter moves that don't resolve it
        return filterCheckResolve(result,cs)
    else:
        return result


# Moves for a king.  Returns a list of chessMove (or empty list)
def getKingMoves(startIndex : int, cs : chessState):
    """Generate legal moves (including castling) for a king at ``startIndex``.

    :param startIndex: Square index of the king (0..63).
    :type startIndex: int
    :param cs: Current board state.
    :type cs: chessState
    :return: List of legal king moves.
    :rtype: list[chessMove]
    """

    def considerKingSideCastle(startIndex:int, cs:chessState, result : list):
        # Can't be in check
        if(hasKingCollision(cs)):
            return
        # color
        is_white = cs.pieceList[startIndex].isupper()
        proceed = False
        # Get eligible squares
        if(is_white) and (cs.castle_white_king):
            proceed = True
            sk = 60
            s1 = 61
            s2 = 62
            sr = 63
        if(not is_white) and (cs.castle_black_king):
            proceed = True
            sk = 4
            s1 = 5
            s2 = 6
            sr = 7
        if(proceed == False):
            return
        
        # Look for pieces blocking castle
        if(cs.pieceList[s1] != None):
            return

        if(cs.pieceList[s2] != None):
            return
        
        # Look for threats on these squares
        for idx,p in enumerate(cs.pieceList):
            # For opposite colors
            if(p != None) and (p.upper() != "K") and (p.isupper() != is_white):
                moves = getMovesFromSquare(idx,cs,False)
                for m in moves:
                    if(m.end == s1) or (m.end == s2) or (m.end == sk) or (m.end == sr):
                        return
        
        # Valid castle
        result.append(chessMove(sk,s2,castleRookSquares=[sr,s1]))
            
    def considerQueenSideCastle(startIndex:int, cs:chessState, result : list):
        # Can't be in check
        if(hasKingCollision(cs)):
            return
        # color
        is_white = cs.pieceList[startIndex].isupper()
        proceed = False
        # Get eligible squares
        if(is_white) and (cs.castle_white_queen):
            proceed = True
            sk = 60
            s1 = 59
            s2 = 58
            s3 = 57
            sr = 56
        if(not is_white) and (cs.castle_black_queen):
            proceed = True
            sk = 4
            s1 = 3
            s2 = 2
            s3 = 1
            sr = 0
        if(proceed == False):
            return
        
        # Look for pieces blocking castle
        if(cs.pieceList[s1] != None):
            return

        if(cs.pieceList[s2] != None):
            return
        
        # Look for threats on these squares
        for idx,p in enumerate(cs.pieceList):
            # For opposite colors
            if(p != None) and (p.upper() != "K") and (p.isupper() != is_white):
                moves = getMovesFromSquare(idx,cs,False)
                for m in moves:
                    if(m.end == s1) or (m.end == s2) or (m.end == s3) or (m.end == sk) or (m.end == sr):
                        return
        
        # Valid castle
        result.append(chessMove(sk,s2,castleRookSquares=[sr,s1]))


    # Consider and individual move
    def considerKingMove(move, startIndex: int, cs: chessState, result : list):
        endIndex = move(startIndex)
        collisionType = getCollisionType(startIndex,endIndex,cs)
        move = None
        match collisionType:
            case 0: # Invalid
                return 
            case 1: # Normal
                # Move
                move = chessMove(startIndex,endIndex)
            case 2: # Same color
                return 
            case 3: # Opposite color
                move = chessMove(startIndex,endIndex,is_capture=True) 
            case 4: # Opposite King
                return         
        pretendGame = copy.deepcopy(cs)
        movePiece(move,pretendGame,False)
        pretendGame.toggle_turn()
        in_check = hasKingCollision(pretendGame)
        if(not in_check):
           result.append(move)

    # Coniser all king moves
    def considerKingMoves(startIndex: int, cs: chessState, result : list): 
        # Block
        considerKingMove(squareUp,startIndex,cs,result)
        considerKingMove(squareUpLeft,startIndex,cs,result)
        considerKingMove(squareLeft,startIndex,cs,result)
        considerKingMove(squareDownLeft,startIndex,cs,result)
        considerKingMove(squareDown,startIndex,cs,result)
        considerKingMove(squareDownRight,startIndex,cs,result)
        considerKingMove(squareRight,startIndex,cs,result)
        considerKingMove(squareUpRight,startIndex,cs,result)
        # Castle
        considerKingSideCastle(startIndex,cs,result)
        considerQueenSideCastle(startIndex,cs,result)

    result = []
    considerKingMoves(startIndex,cs,result)
    return result


# Return a list of valid moves from a given square
# Each move is tuple with (idx,type_of_move) where 
# type_of_move can be "X"=capture", "N"=normal, "E"=en passant, 
# "P"=promotion, "C"=check, or "K,k,Q,q" for castling in that direction
def getMovesFromSquare(start : int, cs : chessState, filterForCheck = True):
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
    piece = cs.pieceList[start]
    match piece.upper():
        case "P":
            return getPawnMoves(start,cs,filterForCheck)
        case "N":
            return getKnightMoves(start,cs,filterForCheck) 
        case "B":
            return getBishopMoves(start,cs,filterForCheck)  
        case "R":
            return getRookMoves(start,cs,filterForCheck)    
        case "Q":
            return getQueenMoves(start,cs,filterForCheck)   
        case "K":
            return getKingMoves(start,cs)                                    
        case _:
            return []
    
if __name__ == "__main__":
    None
