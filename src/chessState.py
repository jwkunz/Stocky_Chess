"""Board state representation and FEN serialization for Stocky Chess."""

from enum import Enum


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
    :ivar enpassant_targets: Algebraic target square for en passant or ``'-'``.
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
        # Databases
        self.pieceList = []
        for i in range(64):
            self.pieceList.append(None)
        # Turn character
        self.turn = ""
        # Castle flags
        self.castle_black_king = False
        self.castle_black_queen = False
        self.castle_white_king = False
        self.castle_white_queen = False
        # En Passant
        self.enpassant_targets = "-"
        # Half move counter
        self.half_move = 0
        # Full move counter
        self.full_move = 0
        # Flags
        self.promotable = False # indicates the .turn has a promotion

    # Sets all the positions to start of game
    def setNewGame(self):
        """Reset the board to the standard chess starting position."""
        self.setFENstring("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    # Get the current board's fen string
    def getFENstring(self):
        """Serialize the current board state into a Forsyth-Edwards Notation (FEN) string.

        :return: The FEN string representing the current state.
        :rtype: str
        """
        fen = ""
        blank_counter = 0
        for i in range(8):
            for j in range(8):
                idx = i*8+j
                endrow = (j == 7)
                if(self.pieceList[idx] == None):
                    blank_counter += 1
                    if(endrow):
                        fen += str(blank_counter)
                        fen += "/"
                        blank_counter = 0
                else:
                    if(blank_counter > 0):
                        fen += str(blank_counter)
                        blank_counter = 0

                    fen += self.pieceList[idx]
                    if(endrow):
                        fen += "/"

        # Get rid of last token
        fen = fen[0:-1]
        
        # Turn
        fen += f" {self.turn} "

        # Castling
        fen_castle = ""
        if(self.castle_white_king):
            fen_castle += 'K'
        if(self.castle_white_queen):
            fen_castle += 'Q'
        if(self.castle_black_king):
            fen_castle += 'k'
        if(self.castle_black_queen):
            fen_castle += 'q'
        if(fen_castle == ""):
            fen_castle = "-"  
        fen += f"{fen_castle} "          

        # Other fields
        fen += f"{self.enpassant_targets} "
        fen += f"{self.half_move} "
        fen += f"{self.full_move}"

        # return
        return fen
    

    # Set the board to a given FEN string
    def setFENstring(self,fen : str):
        """Populate the board state from a Forsyth-Edwards Notation (FEN) string.

        :param fen: A space-delimited 6-field FEN string.
        :type fen: str
        """
        # Get the various fields
        fields = fen.split()

        # Reset pieces
        self.pieceList = []
        for i in range(64):
            self.pieceList.append(None)

        # Store FEN into pieceList
        # idx=0 -> r=0 c=0 -> "A8", idx=63 -> r=7 c=7 -> "H1"
        row_counter = 0
        column_counter = 0
        for token in fields[0]:
            pos = row_counter*8 + column_counter
            if(token.isdigit()):
                # Advance the rolumn counter
                column_counter += int(token)
                continue
            if(token == " "):
                # Skip
                continue
            if(token == "/"):
                # End of row
                row_counter += 1
                column_counter = 0
                continue
            self.pieceList[pos] = token
            column_counter += 1

        # Store FEN turn
        self.turn = fields[1]

        # Castle rights
        self.castle_black_king = False
        self.castle_black_queen = False
        self.castle_white_king = False
        self.castle_white_queen = False
        for token in fields[2]:
            match token:
                case "k":
                    self.castle_black_king = True
                case "q":
                    self.castle_black_queen = True                    
                case "K":
                    self.castle_white_king = True
                case "Q":
                    self.castle_white_queen = True
                case _: 
                    # Other or -
                    None
        
        # En Passant
        self.enpassant_targets = fields[3]

        # Half move counter
        self.half_move = int(fields[4])

        # Full move counter
        self.full_move = int(fields[5])

    # Goes white to black.  Does not handle half moves
    def toggle_turn(self):
        """Switch the active turn between White and Black and increment full moves after Black's turn."""
        if(self.turn == "w"):
            self.turn = "b"
        else:
            self.turn = "w"
            self.full_move += 1

if __name__ == "__main__":
    dut = chessState()
    dut.setNewGame()
    print(dut.getFENstring())
