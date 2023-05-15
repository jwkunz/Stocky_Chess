from enum import Enum

class player_t(Enum):
    BLACK = 0
    WHITE = 1

class piece_t(Enum):
    KING = 0
    QUEEN = 1
    BISHOP = 2
    KNIGHT = 3
    ROOK = 4
    PAWN = 5

class chessState:
    
    def __init__(self):
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
        self.setFENstring("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    # Get the current board's fen string
    def getFENstring(self):
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
        if(self.turn == "w"):
            self.turn = "b"
        else:
            self.turn = "w"
            self.full_move += 1

if __name__ == "__main__":
    dut = chessState()
    dut.setNewGame()
    print(dut.getFENstring())