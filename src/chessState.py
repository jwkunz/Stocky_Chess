"""Board state representation and FEN serialization for Stocky Chess."""

from enum import Enum
import copy


START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
VALID_PIECES = frozenset("PNBRQKpnbrqk")


class player_t(Enum):
    """Enumeration of chess players by color."""

    BLACK = 0
    WHITE = 1


class piece_t(Enum):
    """Enumeration of chess piece types."""

    KING = 0
    QUEEN = 1
    BISHOP = 2
    KNIGHT = 3
    ROOK = 4
    PAWN = 5


class chessState:
    """Represents a complete chess position including board squares and FEN metadata.

    :ivar pieceList: List of 64 square values (index 0 is A8, index 63 is H1),
        containing single-character piece codes or ``None``.
    :vartype pieceList: list[str | None]
    :ivar turn: Active player color (``'w'`` or ``'b'``).
    :vartype turn: str
    :ivar castle_black_king: Whether Black can castle kingside.
    :vartype castle_black_king: bool
    :ivar castle_black_queen: Whether Black can castle queenside.
    :vartype castle_black_queen: bool
    :ivar castle_white_king: Whether White can castle kingside.
    :vartype castle_white_king: bool
    :ivar castle_white_queen: Whether White can castle queenside.
    :vartype castle_white_queen: bool
    :ivar enpassant_targets: Algebraic target square for en passant (uppercase, e.g. ``'E3'``) or ``'-'``.
    :vartype enpassant_targets: str
    :ivar half_move: Half-move clock since the last pawn advance or capture.
    :vartype half_move: int
    :ivar full_move: Full-move number, incremented after Black's turn.
    :vartype full_move: int
    :ivar promotable: Flag indicating whether the current turn has a promotion.
    :vartype promotable: bool
    """

    def __init__(self):
        """Initialize an empty chess board state with default counters and flags."""
        self.pieceList = [None] * 64
        self.turn = "w"
        self.castle_black_king = False
        self.castle_black_queen = False
        self.castle_white_king = False
        self.castle_white_queen = False
        self.enpassant_targets = "-"
        self.half_move = 0
        self.full_move = 1
        self.promotable = False

    def copy(self) -> "chessState":
        """Return a deep copy of this chessState.

        :return: Cloned chessState instance.
        :rtype: chessState
        """
        cloned = chessState()
        cloned.pieceList = list(self.pieceList)
        cloned.turn = self.turn
        cloned.castle_black_king = self.castle_black_king
        cloned.castle_black_queen = self.castle_black_queen
        cloned.castle_white_king = self.castle_white_king
        cloned.castle_white_queen = self.castle_white_queen
        cloned.enpassant_targets = self.enpassant_targets
        cloned.half_move = self.half_move
        cloned.full_move = self.full_move
        cloned.promotable = self.promotable
        return cloned

    def __eq__(self, other: object) -> bool:
        """Compare two chessState objects for full equality."""
        if not isinstance(other, chessState):
            return False
        return (
            self.pieceList == other.pieceList
            and self.turn == other.turn
            and self.castle_white_king == other.castle_white_king
            and self.castle_white_queen == other.castle_white_queen
            and self.castle_black_king == other.castle_black_king
            and self.castle_black_queen == other.castle_black_queen
            and self.enpassant_targets == other.enpassant_targets
            and self.half_move == other.half_move
            and self.full_move == other.full_move
        )

    def setNewGame(self):
        """Reset the board to the standard chess starting position."""
        self.setFENstring(START_FEN)

    def getFENstring(self) -> str:
        """Serialize the current board state into a Forsyth-Edwards Notation (FEN) string.

        :return: The FEN string representing the current state.
        :rtype: str
        """
        rows = []
        for r in range(8):
            row_str = ""
            blank_counter = 0
            for c in range(8):
                piece = self.pieceList[r * 8 + c]
                if piece is None:
                    blank_counter += 1
                else:
                    if blank_counter > 0:
                        row_str += str(blank_counter)
                        blank_counter = 0
                    row_str += piece
            if blank_counter > 0:
                row_str += str(blank_counter)
            rows.append(row_str)

        board_part = "/".join(rows)

        fen_castle = ""
        if self.castle_white_king:
            fen_castle += "K"
        if self.castle_white_queen:
            fen_castle += "Q"
        if self.castle_black_king:
            fen_castle += "k"
        if self.castle_black_queen:
            fen_castle += "q"
        if not fen_castle:
            fen_castle = "-"

        ep = self.enpassant_targets.lower() if self.enpassant_targets != "-" else "-"
        return f"{board_part} {self.turn} {fen_castle} {ep} {self.half_move} {self.full_move}"

    def getPositionKey(self) -> str:
        """Return the four-field FEN position key used for threefold repetition detection.

        Includes piece placement, active color, castling availability, and en passant target.

        :return: Space-delimited 4-field position signature.
        :rtype: str
        """
        fields = self.getFENstring().split()
        return " ".join(fields[:4])

    def setFENstring(self, fen: str):
        """Populate and validate the board state from a Forsyth-Edwards Notation (FEN) string.

        :param fen: A space-delimited 6-field FEN string.
        :type fen: str
        :raises ValueError: If the FEN string is malformed.
        """
        if not isinstance(fen, str) or not fen.strip():
            raise ValueError("FEN string cannot be empty.")

        fields = fen.strip().split()
        if len(fields) != 6:
            raise ValueError(f"Expected 6 fields in FEN string, got {len(fields)}.")

        ranks = fields[0].split("/")
        if len(ranks) != 8:
            raise ValueError(f"Expected 8 ranks in FEN board, got {len(ranks)}.")

        new_pieces = [None] * 64
        for r_idx, rank_str in enumerate(ranks):
            col_idx = 0
            for ch in rank_str:
                if ch.isdigit():
                    col_idx += int(ch)
                elif ch in VALID_PIECES:
                    if col_idx >= 8:
                        raise ValueError(f"Rank {8 - r_idx} exceeds 8 files.")
                    new_pieces[r_idx * 8 + col_idx] = ch
                    col_idx += 1
                else:
                    raise ValueError(f"Invalid piece character '{ch}' in FEN.")
            if col_idx != 8:
                raise ValueError(f"Rank {8 - r_idx} has {col_idx} squares instead of 8.")

        turn_field = fields[1].lower()
        if turn_field not in ("w", "b"):
            raise ValueError(f"Invalid turn field '{fields[1]}'; expected 'w' or 'b'.")

        castle_field = fields[2]
        if castle_field != "-" and any(c not in "KQkq" for c in castle_field):
            raise ValueError(f"Invalid castling availability '{castle_field}'.")

        ep_field = fields[3]
        if ep_field != "-":
            if len(ep_field) != 2 or ep_field[0].lower() not in "abcdefgh" or ep_field[1] not in "36":
                raise ValueError(f"Invalid en passant target square '{ep_field}'.")
            ep_normalized = ep_field.upper()
        else:
            ep_normalized = "-"

        half_move = int(fields[4])
        full_move = int(fields[5])
        if half_move < 0 or full_move < 1:
            raise ValueError("Half-move clock must be >= 0 and full-move number must be >= 1.")

        self.pieceList = new_pieces
        self.turn = turn_field
        self.castle_white_king = "K" in castle_field
        self.castle_white_queen = "Q" in castle_field
        self.castle_black_king = "k" in castle_field
        self.castle_black_queen = "q" in castle_field
        self.enpassant_targets = ep_normalized
        self.half_move = half_move
        self.full_move = full_move

    def toggle_turn(self):
        """Switch the active turn between White and Black and increment full moves after Black's turn."""
        if self.turn == "w":
            self.turn = "b"
        else:
            self.turn = "w"
            self.full_move += 1


if __name__ == "__main__":
    dut = chessState()
    dut.setNewGame()
    print(dut.getFENstring())
