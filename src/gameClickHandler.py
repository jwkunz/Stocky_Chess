"""State machine for handling user board clicks and triggering engine moves."""

# This class collects user clicks at x,y or bot moves and operates the game
from chessBoard import chessBoard_widget
from chessState import player_t, chessState
from chessAdmin import getMovesFromSquare, movePiece,isGameOver,chessMove,convertLabel
from gameLog import gameLog
from PyQt6.QtWidgets import QMainWindow
from uciEngine import uciEngine
import time


class gameClickHandler:
    """Processes mouse clicks on the board and coordinates turn transitions and engine play.

    :ivar action_state: Current state of the turn/selection state machine
        (e.g. ``'WHITE_SELECT_PIECE'``, ``'WHITE_SELECT_MOVE'``, ``'BLACK_SELECT_PIECE'``,
        ``'BLACK_SELECT_MOVE'``, ``'CHECKMATE'``, ``'STALEMATE'``, ``'TIMEOUT'``).
    :vartype action_state: str
    :ivar action_idx: Currently selected square index (0-63), or 64/None when unselected.
    :vartype action_idx: int | None
    :ivar highlighed_moves: Currently highlighted legal moves for the selected piece.
    :vartype highlighed_moves: list[chessMove] | None
    """

    def __init__(self):
        """Initialize the click handler starting on White's piece selection."""
        self.action_state = "WHITE_SELECT_PIECE"
        self.action_idx = 64
        self.highlighed_moves = []

    # Set who's turn it is in the click state machine
    def setWhosTurn(self, whosMove : player_t):
        """Set the state machine to wait for piece selection by the specified player.

        :param whosMove: Player enum indicating whose turn it is.
        :type whosMove: player_t
        """
        if(whosMove == player_t.WHITE):
            self.action_state = "WHITE_SELECT_PIECE"
        else:
            self.action_state = "BLACK_SELECT_PIECE"

    # This function is to consolidate repeated code
    def _F1(self, idx : int, nextState : str, cs : chessState, cb : chessBoard_widget):
        """Compute legal moves for the selected square, highlight them, and advance state.

        :param idx: Selected board square index (0-63).
        :type idx: int
        :param nextState: State machine state to transition to if legal moves exist.
        :type nextState: str
        :param cs: Current chess board state.
        :type cs: chessState
        :param cb: Chess board widget to render highlights on.
        :type cb: chessBoard_widget
        """
        # Get available moves
        moves = getMovesFromSquare(idx,cs)
        if(len(moves) > 0):
            # Highlight
            self.highlighed_moves = moves
            # Render
            cb.renderBoard(cs,moves)
            # Log index
            self.action_idx = idx
            # Next state
            self.action_state = nextState

    # This function is to consolidate repeated code
    def _F2(self, idx : int, nextState : str, cs : chessState, cb : chessBoard_widget, gl : gameLog, mainWindow : QMainWindow):
        """Execute a selected destination move if it matches one of the highlighted legal moves.

        :param idx: Destination square index clicked by the player.
        :type idx: int
        :param nextState: Next state to transition to if the game continues.
        :type nextState: str
        :param cs: Current chess state to mutate.
        :type cs: chessState
        :param cb: Chess board widget to re-render.
        :type cb: chessBoard_widget
        :param gl: Game log to record the new board state.
        :type gl: gameLog
        :param mainWindow: Main application window for promotion dialogs and move narration.
        :type mainWindow: QMainWindow
        """
        # Look for promotions
        pType = "" # Used for promotions
        for m in self.highlighed_moves:
            # Look for promtions
            if (m.end == idx) and (m.promotionPiece != ""):
                # Window action for promotions
                pType = mainWindow.promotionCallback(cs.pieceList[m.start].isupper())
                break
        
        # Look for click in highlighted moves
        for m in self.highlighed_moves:
            if(m.end == idx) and (m.promotionPiece == pType) and (m.is_check == False):
                self.highlighed_moves = None
                # Move
                mainWindow.movePieceWithAnimation(m,cs)
                # Log
                gl.addState(cs)
                # Look for game over conditions
                match isGameOver(cs):
                    case 0: 
                        # Normal continue game
                        self.action_state = nextState
                    case 1:
                        # Checkmate
                        self.action_state = "CHECKMATE"
                    case 2:
                        # Stalemate
                        self.action_state = "STALEMATE"
                # Update action index
                self.action_idx = None
                # Render
                cb.renderBoard(cs)     
                return

    # Get's and enginem move
    def engineHandler(self,engine : uciEngine,cs : chessState, cb : chessBoard_widget, gl : gameLog, mainWindow : QMainWindow):
        """Request a move from a UCI engine, apply it to the board state, and check for game end.

        :param engine: Configured UCI engine instance.
        :type engine: uciEngine
        :param cs: Current chess state.
        :type cs: chessState
        :param cb: Chess board widget to render the updated state.
        :type cb: chessBoard_widget
        :param gl: Game log to append the resulting position.
        :type gl: gameLog
        :param mainWindow: Main window instance for timer updates and move narration.
        :type mainWindow: QMainWindow
        """
        # Engine run
        argDict = {"inputFEN":cs.getFENstring()}
        engine.tick(argDict)
        while(engine.current_state != "WAITING"):
            # Simulate time passage while blocking
            engine.tick(argDict)
            time.sleep(mainWindow.loopTimeMS/1000.0)
            mainWindow.timerCallback()
            # Refresh
            mainWindow.repaint()

        # Act on best move
        bestMove = argDict["bestMove"]
        # Start
        startPos = bestMove[0:2]
        [c,r,startIndex] = convertLabel(startPos)
        # End
        endPos = bestMove[2:4]
        [c,r,endIndex] = convertLabel(endPos)

        # Promotion
        promotion = ""
        if(len(bestMove)==5):
            promotion= bestMove[4]
            if(cs.turn == "w"):
                promotion = promotion.upper()
            else:
                promotion = promotion.lower()

        # Match against legal moves from startIndex so castling, en passant, captures, and check flags are preserved
        selectedMove = None
        for candidate in getMovesFromSquare(startIndex, cs):
            if (candidate.end == endIndex) and (candidate.promotionPiece == promotion) and (not candidate.is_check):
                selectedMove = candidate
                break
        if selectedMove is None:
            selectedMove = chessMove(startIndex, endIndex, is_capture=(cs.pieceList[endIndex] is not None), promotionPiece=promotion)
       
        # Make Move
        mainWindow.movePieceWithAnimation(selectedMove,cs)

        # Look for game over conditions
        match isGameOver(cs):
            case 0: 
                if(cs.turn == "w"):
                    self.action_state = "WHITE_SELECT_PIECE"
                else:
                    self.action_state = "BLACK_SELECT_PIECE"
            case 1:
                # Checkmate
                self.action_state = "CHECKMATE"
                if(cs.turn == "w"):
                    mainWindow.whiteDisplay.append("White loses by checkmate")
                    mainWindow.blackDisplay.append("Black wins by checkmate")
                else:
                    mainWindow.whiteDisplay.append("White wins by checkmate")
                    mainWindow.blackDisplay.append("Black loses by checkmate")                      
            case 2:
                # Stalemate
                self.action_state = "STALEMATE"
                mainWindow.whiteDisplay.append("Game ends in stalemate")
                mainWindow.blackDisplay.append("Game ends in stalemate")
        # Log
        gl.addState(cs)
        # Render
        cb.renderBoard(cs)

    # This state machine handles user clicks or bot moves and takes action
    def clickHandler(self, x : int, y : int, cs : chessState, cb : chessBoard_widget, gl : gameLog, mainWindow : QMainWindow):
        """Dispatch a user click at ``(x, y)`` or a bot turn (when coordinates are ``None``).

        :param x: Scene X coordinate in pixels, or ``None`` for an engine turn.
        :type x: int | float | None
        :param y: Scene Y coordinate in pixels, or ``None`` for an engine turn.
        :type y: int | float | None
        :param cs: Active chess state.
        :type cs: chessState
        :param cb: Chess board widget.
        :type cb: chessBoard_widget
        :param gl: Move history log.
        :type gl: gameLog
        :param mainWindow: Main window controller.
        :type mainWindow: QMainWindow
        """
        # x or y = None signifies this is a bot move
        if(x != None) and (y!= None):
            idx = cb.coordToSquare(x,y)
            # Make sure not out of range
            if(idx >= 64):
                # If so, quit
                return 
            clickedPiece = cs.pieceList[idx]
        
        # Take action
        match self.action_state:              
            case "WHITE_SELECT_PIECE":
                # Check for engine move
                if(mainWindow.whiteEngine != None):
                    self.engineHandler(mainWindow.whiteEngine,cs,cb,gl,mainWindow)
                # Clicked empty square
                elif(clickedPiece == None):
                    None
                elif(clickedPiece.isupper()):
                    self._F1(idx,"WHITE_SELECT_MOVE",cs,cb)

            case "WHITE_SELECT_MOVE":
                # Pick same index to cancel highlighting
                if(idx == self.action_idx):
                    self.highlighed_moves = []
                    self.action_idx = None
                    cb.renderBoard(cs)
                    self.action_state = "WHITE_SELECT_PIECE"       
                # Change if picking a another white piece
                elif(clickedPiece != None) and (clickedPiece.isupper()):
                    self._F1(idx,"WHITE_SELECT_MOVE",cs,cb)  
                else:      
                    self._F2(idx,"BLACK_SELECT_PIECE",cs,cb,gl,mainWindow)           

            case "BLACK_SELECT_PIECE":
                # Check for engine move
                if(mainWindow.blackEngine != None):
                    self.engineHandler(mainWindow.blackEngine,cs,cb,gl,mainWindow)                        
                # Clicked empty square
                elif(clickedPiece == None):
                    None
                elif(clickedPiece.islower()):
                    self._F1(idx,"BLACK_SELECT_MOVE",cs,cb)

            case "BLACK_SELECT_MOVE":
                # Pick same index to cancel highlighting
                if(idx == self.action_idx):
                    self.highlighed_moves = []
                    self.action_idx = None
                    cb.renderBoard(cs)
                    self.action_state = "BLACK_SELECT_PIECE"                 
                # Change if picking a another black piece
                elif(clickedPiece != None) and (clickedPiece.islower()):
                    self._F1(idx,"BLACK_SELECT_MOVE",cs,cb)  
                else:      
                    self._F2(idx,"WHITE_SELECT_PIECE",cs,cb,gl,mainWindow)  
                                
            case "CHECKMATE":
                None # Dialog handled outside of function

            case "STALEMATE":
                None # Dialog handled outside of function

            case "TIMEOUT":
                None # Dialog handled outside of function


if __name__ == "__main__":
    None
