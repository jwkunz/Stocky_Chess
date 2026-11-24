"""Main PyQt6 application window, dialogs, chess clocks, and event loop for Stocky Chess."""

from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QDialog,QLabel,QTextEdit,QVBoxLayout,QPushButton,QHBoxLayout,QRadioButton,QSpinBox,QTimeEdit,QCheckBox
from PyQt6.QtCore import Qt,QTimer
from chessBoard import chessBoard_widget
from chessState import player_t
from gameClickHandler import gameClickHandler
from gameLog import gameLog
from chessAdmin import chessMove,chessState,movePiece,convertIndex,getPieceTextNameOn,getPiecetoTextName
from uciEngine import uciEngine
import sys
import copy
from math import ceil

loopTimeMS = 100


class Ui(QtWidgets.QMainWindow):
    """Main window controller for the Stocky Chess desktop application.

    Loads the Qt Designer UI from ``resources/StockyChess.ui``, initializes the
    board widget, manages player types (Human or Stockfish), runs the chess clocks,
    and coordinates user and engine moves.

    :cvar version: Application version string.
    :vartype version: str
    """

    version = "1.0.0"

    def __init__(self):
        """Initialize the main window, board widget, signal connections, and default game state."""
        super(Ui, self).__init__()
        # Load the User Interface
        uic.loadUi('resources/StockyChess.ui', self) 
        
        # Create board scene
        S = QtWidgets.QGraphicsScene()
        self.viewport.setScene(S)
        self.viewport.show()
        
        # Create the chess board
        self.chessBoardWidget = chessBoard_widget(self.viewport.width(),self.viewport.width()//40,True)

        # Create game click handler
        self.gameClickHandler = gameClickHandler()

        # Create new game state
        self.startNewGame()

        # Welcome
        self.print_to_console(f"Welcome to Stocky Chess Version {self.version}")
        self.print_to_console(f"Select Menu >> New Game to begin")

        # Memory
        self.FENhistory = []

        # Render everything
        self.render()

        # Actions
        S.mouseReleaseEvent = lambda event : self.boardClick(event)
        self.actionWhite_Bottom.triggered.connect(lambda : self.setBoardDirection(True))
        self.actionBlack_Bottom.triggered.connect(lambda : self.setBoardDirection(False))
        self.actionNew_Game.triggered.connect(self.startNewGame)
        self.actionSetWhite_Human.triggered.connect(lambda : self.setHuman("w"))
        self.actionSetBlack_Human.triggered.connect(lambda : self.setHuman("b"))
        self.actionSetWhite_Stockfish.triggered.connect(lambda : self.setStockfish("w"))
        self.actionSetBlack_Stockfish.triggered.connect(lambda : self.setStockfish("b"))        
        self.actionSetWhiteTimeControlMode.triggered.connect(lambda : self.setTimeControlMode("w"))   
        self.actionSetBlackTimeControlMode.triggered.connect(lambda : self.setTimeControlMode("b"))     
        self.actionImport_FEN.triggered.connect(self.setFENstate)
        self.prevMove.pressed.connect(self.setPrevMove)
        self.nextMove.pressed.connect(self.setNextMove)

        # Engines (None = Human)
        self.setHuman("w")
        self.setHuman("b")

        # GLobal time
        self.runtime_ms = 0
        self.timerState = "IDLE"

        self.loopTimeMS = loopTimeMS

    # Dialog for time control settings
    def setTimeControlMode(self,color : str):
        """Open a modal dialog to configure initial clock time and increment for a player.

        :param color: Player color code (``'w'`` or ``'b'``).
        :type color: str
        """
        # Make Dialog asking a piece selection
        dlg = QDialog(self)

        # Pivot instructions on color
        if(color == "w"):
            dlg.setWindowTitle("Enter Time For White:")
        else:
            dlg.setWindowTitle("Enter Time For Black:")

        # Form
        dlg.layout = QVBoxLayout()

        # Start
        hLayout = QHBoxLayout()
        hLayout.addWidget(QLabel("Initial Time:  "))
        hLayout.addWidget(QLabel("hours"))
        it_hr = QSpinBox()
        it_hr.setMaximum(99)
        it_hr.setMinimum(0)
        it_hr.setValue(0)
        hLayout.addWidget(it_hr)
        hLayout.addWidget(QLabel("minutes"))
        it_mn = QSpinBox()
        it_mn.setMaximum(59)
        it_mn.setMinimum(0)      
        it_mn.setValue(5)  
        hLayout.addWidget(it_mn)
        dlg.layout.addLayout(hLayout)
        hLayout.addWidget(QLabel("seconds"))
        it_sc = QSpinBox()
        it_sc.setMaximum(59)
        it_sc.setMinimum(0)      
        it_sc.setValue(0)  
        hLayout.addWidget(it_sc)
        dlg.layout.addLayout(hLayout)   

        # Increment
        hLayout = QHBoxLayout()
        hLayout.addWidget(QLabel("Move Increment (seconds)"))
        inc_s = QSpinBox()
        inc_s.setMaximum(59)
        inc_s.setMinimum(0)      
        inc_s.setValue(0)  
        hLayout.addWidget(inc_s)
        dlg.layout.addLayout(hLayout)

        # Flags
        hLayout = QHBoxLayout()
        noTime = QCheckBox("No Time Control")
        hLayout.addWidget(noTime)   
        bothPlayers = QCheckBox("Set Both Players")
        hLayout.addWidget(bothPlayers)                
        dlg.layout.addLayout(hLayout)

        # Apply settings
        def apply():
            if(noTime.isChecked()):
                timeMS = 100*60*60*1000 -1
                incMS = 0
                timeDecMS = 0
            else:
                timeMS = 60*60*1000*it_hr.value() + 60*1000*it_mn.value() + 1000*it_sc.value()
                incMS = 1000*inc_s.value()
                timeDecMS = loopTimeMS
            if(color == "w") or bothPlayers.isChecked():
                self.whiteMS = timeMS
                self.whiteTimeIncMS = incMS
                self.whiteTimeDecMS = timeDecMS
            if(color == "b") or bothPlayers.isChecked():
                self.blackMS = timeMS
                self.blackTimeIncMS = incMS
                self.blackTimeDecMS = timeDecMS

        # Button
        applyButton = QPushButton("Apply")
        applyButton.pressed.connect(apply)

        # Generate
        dlg.layout.addWidget(applyButton)
        dlg.setLayout(dlg.layout)
        dlg.exec()

    # Flips board direction
    def setBoardDirection(self,direction : bool):
        """Set the board orientation and re-render.

        :param direction: ``True`` for White at the bottom, ``False`` for Black at the bottom.
        :type direction: bool
        """
        self.chessBoardWidget.white_bottom = direction
        self.render()

    # Set as human player
    def setHuman(self,color : str):
        """Configure the specified side to be controlled by a human player.

        :param color: Player color code (``'w'`` or ``'b'``).
        :type color: str
        """
        if(color == "w"):
            self.whiteEngine = None
            self.whiteType.setText("HUMAN")
        else:
            self.blackEngine = None
            self.blackType.setText("HUMAN")

    # Set as stockfish player
    def setStockfish(self,color : str):
        """Open a dialog to configure Stockfish skill level and depth for the given side.

        :param color: Player color code (``'w'`` or ``'b'``).
        :type color: str
        """
        # Make Dialog asking a piece selection
        dlg = QDialog(self)
        dlg.setWindowTitle("Stockfish:")
        dlg.layout = QVBoxLayout()

        # Difficulty
        label = QLabel("Select Difficulty:")
        dlg.layout.addWidget(label)

        diffDial = QSpinBox()
        diffDial.setMaximum(20)
        diffDial.setMinimum(1)
        diffDial.setValue(10)
        dlg.layout.addWidget(diffDial)


        # Seach depth
        label = QLabel("Select Search Depth:")
        dlg.layout.addWidget(label)

        depthDial = QSpinBox()
        depthDial.setMaximum(30)
        depthDial.setMinimum(1)
        depthDial.setValue(20)
        dlg.layout.addWidget(depthDial)

        # Apply button
        button = QPushButton("Accept")
        dlg.layout.addWidget(button)
        button.pressed.connect(lambda : dlg.close())

        dlg.setLayout(dlg.layout)

        dlg.exec()
        difficulty = diffDial.value()
        moveDepth = depthDial.value()

        # Update player box
        if(color == "w"):
            self.whiteEngine = uciEngine(difficulty=difficulty,moveDepth=moveDepth)
            self.whiteType.setText(f"STOCKFISH LVL {difficulty} DEPTH {moveDepth}")
        else:
            self.blackEngine = uciEngine(difficulty=difficulty,moveDepth=moveDepth)
            self.blackType.setText(f"STOCKFISH LVL {difficulty} DEPTH {moveDepth}")

    # This updates the graphics and various menus
    # The updateBoard flag can be used bypass a chessBoard redraw if 
    # another object already handled that process.  For example, moves, promotions etc...
    def render(self, updateBoard = True):
        """Refresh the board display, FEN bar, turn slider, and material counts.

        :param updateBoard: When ``True``, redraws the board pixmap before updating the scene.
        :type updateBoard: bool
        """
        renderGame = self.gameLog.getGameByIndex(self.gameRenderIndex)
        if(updateBoard):
            self.chessBoardWidget.renderBoard(renderGame)
        fenString =  renderGame.getFENstring()
        self.FENbar.setText(fenString)
        self.viewport.scene().addPixmap(self.chessBoardWidget.pixmap())
        self.update_move_slider(renderGame.turn)
        self.updateMaterial()
        self.repaint()  

    # Starts a new game
    def startNewGame(self):
        """Reset the game log, click state machine, and clocks for a new game."""
        self.gameLog = gameLog()    
        self.gameLog.reset()
        self.gameRenderIndex = 0
        self.gameClickHandler.action_state = "WHITE_SELECT_PIECE"
        # Time control mode
        self.timeControlState = "IDLE"
        self.whiteMS = 100*60*60*1000 -1
        self.blackMS = 100*60*60*1000 -1
        self.whiteTimeIncMS = 0
        self.blackTimeIncMS = 0
        self.whiteTimeDecMS = 0
        self.blackTimeDecMS = 0
        self.render() 

    # Update the material counts
    def updateMaterial(self):
        """Compute and display active material and point balance for White and Black."""
        material = ["",""]
        count = [0,0]

        # Count the pieces of each player, record in the lists [white,black]
        # materials is couted as numbers because it is to be sorted by piece value
        for p in self.gameLog.getGameByIndex(self.gameRenderIndex).pieceList:
            match p:
                case "P":
                    count[0] += 1
                    material[0] += '0'
                case "N":
                    count[0] += 3
                    material[0] += '1'
                case "B":
                    count[0] += 3   
                    material[0] += '2'                 
                case "R":
                    count[0] += 5
                    material[0] += '3'
                case "Q":
                    count[0] += 9    
                    material[0] += '4'  
                case "K":
                    material[0] += '5'                       
                case "p":
                    count[1] += 1
                    material[1] += '6'
                case "n":
                    count[1] += 3
                    material[1] += '7'
                case "b":
                    count[1] += 3   
                    material[1] += '8'                
                case "r":
                    count[1] += 5
                    material[1] += '9'
                case "q":
                    count[1] += 9    
                    material[1] += 'a' 
                case "k":   
                    material[1] += 'b'                       

        # Now sort and remap back to piece labels
        for i,m in enumerate(material):
            # Sort
            material[i] = sorted(material[i])
            for j,c in enumerate(material[i]):
                match c:
                    case '0':
                        material[i][j] = 'P'
                    case '1':
                        material[i][j] = 'N'
                    case '2':
                        material[i][j] = 'B'
                    case '3':
                        material[i][j] = 'R'
                    case '4':
                        material[i][j] = 'Q'
                    case '5':
                        material[i][j] = 'K'
                    case '6':
                        material[i][j] = 'p'
                    case '7':
                        material[i][j] = 'n'
                    case '8':
                        material[i][j] = 'b'
                    case '9':
                        material[i][j] = 'r'
                    case 'a':
                        material[i][j] = 'q'
                    case 'b':
                        material[i][j] = 'k'                        
            # Make string
            material[i] = ''.join(material[i])

        # Add the balance  marker
        balance = count[0]-count[1]
        if(balance > 0):
            self.materialWhite.setText(f"{material[0]}   (+{balance})")
            self.materialBlack.setText(material[1])
        elif(balance < 0):
            self.materialWhite.setText(material[0])
            self.materialBlack.setText(f"(+{-balance})   {material[1]}")
        else:
            self.materialWhite.setText(material[0])    
            self.materialBlack.setText(material[1])      


    # Updates the marker for who's move
    def update_move_slider(self, turn : str):
        """Update the UI turn indicator slider based on whose turn it is.

        :param turn: ``'w'`` for White or ``'b'`` for Black.
        :type turn: str
        """
        if(turn == 'b'):
            self.moveSlider.setValue(1)
        else:
            self.moveSlider.setValue(0)

    # Prints to shared console
    def print_to_console(self,s : str):
        """Append a message line to the shared console widget.

        :param s: Message text to append.
        :type s: str
        """
        self.printConsole.append(s)

    # Moves piece and updates narrations
    def movePieceWithAnimation(self,move : chessMove, cs : chessState, filterForCheck = True):
        """Log move narration, update player clocks, and apply the move to ``cs``.

        :param move: Move descriptor to execute.
        :type move: chessMove
        :param cs: Board state to mutate.
        :type cs: chessState
        :param filterForCheck: Passed through to :func:`chessAdmin.movePiece`.
        :type filterForCheck: bool
        """
        [r,c,startLabel] = convertIndex(move.start)
        startPieceName = getPieceTextNameOn(move.start,cs).capitalize()

        # Convert end move to narration text
        [r,c,endLabel] = convertIndex(move.end)
        endPieceName = getPieceTextNameOn(move.end,cs)
        # Handle captures
        if(endPieceName != None):
            endLabel = f"capture {endPieceName} on {endLabel}"  

        enPassantText = ""
        if(move.enpassantFlag and (move.is_capture)):
            enPassantText = f" and captured with en passant"

        moveText = ""
        if(len(move.castleRookSquares) > 0):
            moveText = "castles"
        else:
            moveText = "moves"

        promoteText = ""
        if(move.promotionPiece != ""):
            name = getPiecetoTextName(move.promotionPiece)
            promoteText = f" and promote to {name}"

        checkText = ""
        if(move.is_check):
            checkText = " for check"

        # Print the narration
        if(cs.turn == "w"):
            self.whiteDisplay.append(f"{cs.full_move}. {startPieceName} {moveText} from {startLabel} to {endLabel}{enPassantText}{promoteText}{checkText}.")
            self.whiteMS += self.whiteTimeIncMS
            self.writeMS(self.whiteMS,cs.turn)
            self.timeControlState = "BLACK_DEC"
        else:
            self.blackDisplay.append(f"{cs.full_move}. {startPieceName} {moveText} from {startLabel} to {endLabel}{enPassantText}{promoteText}{checkText}.")
            self.blackMS += self.blackTimeIncMS
            self.writeMS(self.blackMS,cs.turn)
            self.timeControlState = "WHITE_DEC"
            

        # Do the move
        movePiece(move,cs,filterForCheck)

    # Handles user clicks and bot moves if event = None
    def boardClick(self, event):
        """Handle a mouse release event on the board scene or trigger an engine move when ``event`` is ``None``.

        :param event: QGraphicsSceneMouseEvent for human clicks, or ``None`` for engine turns.
        :type event: QtWidgets.QGraphicsSceneMouseEvent | None
        """
        # Forking a game branch
        tempLog = copy.deepcopy(self.gameLog)
        tempGame = copy.deepcopy(tempLog.currentGame())

        # Handle game interaction
        if(event != None):
            # Human
            self.gameClickHandler.clickHandler(event.scenePos().x(),event.scenePos().y(),tempGame,self.chessBoardWidget, tempLog, self)
        else:
            # Bot
            self.timerState = "ENGINE_RUNNING"
            self.gameClickHandler.clickHandler(None,None,tempGame,self.chessBoardWidget, tempLog, self)
        
        # Update log if move
        if(len(tempLog.log) > len(self.gameLog.log)):
            self.gameLog = tempLog
            # Update the gameRenderIndex
            self.gameRenderIndex = self.gameLog.getCurrentIndex()
        # This has the false flag because the handler already did renders for moves and such
        self.render(False)
        # Handle end of game message
        if(self.gameClickHandler.action_state == "CHECKMATE"):
            # Window action
            self.checkmateCallback()
        elif(self.gameClickHandler.action_state == "STALEMATE"):
            # Window action
            self.stalemateCallback()

        # Set this to let the rendering catch up
        self.timerState = "DRAW_WAIT"

    # Handles checkmates
    def checkmateCallback(self):
        """Display a modal notification dialog announcing checkmate."""
        # Make Dialog asking a piece selection
        dlg = QDialog(self)
        dlg.setWindowTitle(" ")
        dlg.layout = QVBoxLayout()
        dlg.layout.addWidget(QLabel("Checkmate!"))
        dlg.setLayout(dlg.layout)
        dlg.exec()

    # Handles stalemates
    def stalemateCallback(self):
        """Display a modal notification dialog announcing stalemate."""
        # Make Dialog asking a piece selection
        dlg = QDialog(self)
        dlg.setWindowTitle(" ")
        dlg.layout = QVBoxLayout()
        dlg.layout.addWidget(QLabel("Stalemate!"))
        dlg.setLayout(dlg.layout)
        dlg.exec()

    # Handles timeouts
    def timeoutCallback(self,color : str):
        """Transition the game to ``TIMEOUT`` and display an out-of-time dialog.

        :param color: Player color that ran out of time (``'w'`` or ``'b'``).
        :type color: str
        """
        self.gameClickHandler.action_state = "TIMEOUT"
        # Make Dialog asking a piece selection
        dlg = QDialog(self)
        dlg.setWindowTitle(" ")
        dlg.layout = QVBoxLayout()
        dlg.layout.addWidget(QLabel("Out of time!"))
        dlg.setLayout(dlg.layout)
        dlg.exec()

    # GUI to handle promotions
    def promotionCallback(self, is_white : bool):
        """Display a modal dialog prompting the player to choose a pawn promotion piece.

        :param is_white: ``True`` if the promoting player is White, ``False`` for Black.
        :type is_white: bool
        :return: Single-character FEN symbol for the chosen promotion piece.
        :rtype: str
        """
        # Make Dialog asking a piece selection
        dlg = QDialog(self)
        dlg.setWindowTitle("Select a promotion piece:")
        dlg.layout = QVBoxLayout()

        # Choices
        buttonGroup_layout = QHBoxLayout()
        promtion_group=QtWidgets.QButtonGroup(dlg) 
        r0=QRadioButton("Queen")
        promtion_group.addButton(r0,0)
        r0.setChecked(True)
        buttonGroup_layout.addWidget(r0)
        r1=QRadioButton("Rook")
        promtion_group.addButton(r1,1)
        buttonGroup_layout.addWidget(r1)
        r2=QRadioButton("Bishop")
        promtion_group.addButton(r2,2) 
        buttonGroup_layout.addWidget(r2)
        r3=QRadioButton("Knight")
        promtion_group.addButton(r3,3)                
        buttonGroup_layout.addWidget(r3)

        # Apply button
        button = QPushButton("Apply")

        # Import the string
        def apply():
            val = ""
            match(promtion_group.checkedId()):
                case 0 :
                    val = "q"
                case 1 :
                    val = "r"                    
                case 2 :
                    val = "b"  
                case 3 :
                    val = "n"  
                case _:
                    val = "q"
            # Return int=ord() of char with appropriate color
            if(is_white):
                dlg.done(ord(val.upper()))
            else:
                dlg.done(ord(val.lower()))

        # Layout
        button.pressed.connect(apply)
        dlg.layout.addLayout(buttonGroup_layout)
        dlg.layout.addWidget(button)
        dlg.setLayout(dlg.layout)

        # Run until exit
        code = dlg.exec()

        # If terminated early, default to Queen
        if(code == 0):
            if(is_white):
                return "Q"
            else:
                return "q"
        # Translate code to char
        return chr(code)

    def setFENstate(self):
        """Open a dialog allowing the user to paste and load a custom FEN string."""
        # Make Dialog asking for string
        dlg = QDialog(self)
        dlg.setWindowTitle("FEN Import")
        dlg.layout = QVBoxLayout()
        message = QLabel("Paste in a FEN String")
        text = QTextEdit()
        button = QPushButton("Apply")

        # Import the string
        def update():
            FENstr = text.toPlainText()
            # Currently no error checking....
            self.startNewGame()
            self.gameLog.log[self.gameRenderIndex].setFENstring(FENstr)
            if(self.gameLog.currentGame().turn == "w"):
                self.gameClickHandler.setWhosTurn(player_t.WHITE)
            else:
                self.gameClickHandler.setWhosTurn(player_t.BLACK)
            self.render(True)

        # Layout
        button.pressed.connect(update)
        dlg.layout.addWidget(message)
        dlg.layout.addWidget(text)
        dlg.layout.addWidget(button)
        dlg.setLayout(dlg.layout)
        # Run until exit
        dlg.exec()
    
    def setPrevMove(self):
        """Step backward one ply in the move history log and re-render the board."""
        self.gameRenderIndex -= 1
        if(self.gameRenderIndex < 0):
            self.gameRenderIndex = 0
            return
        self.render(True)
        return

    def setNextMove(self):
        """Step forward one ply in the move history log and re-render the board."""
        self.gameRenderIndex += 1
        if(self.gameRenderIndex > self.gameLog.getCurrentIndex()):
            self.gameRenderIndex = self.gameLog.getCurrentIndex()
            return
        self.render(True)
        return

    # Write milliseconds
    def writeMS(self,ms : int, turn : str):
        """Format a millisecond duration as ``HH:MM:SS.d`` and display it on the player's clock.

        :param ms: Remaining time in milliseconds.
        :type ms: int
        :param turn: ``'w'`` for White's clock or ``'b'`` for Black's clock.
        :type turn: str
        """
        hours =  ms // (1000*60*60)
        minutes = ms // (1000*60) % 60
        seconds = ms // (1000) % 60
        milliseconds = (ms % 1000)//100 
        line = "{0:02.0f}:{1:02.0f}:{2:02.0f}.{3:01.0f}".format(hours,minutes,seconds,milliseconds)
        if(turn == "w"):
            self.whiteTime.setText(line)
        else:
            self.blackTime.setText(line)

    # This is the state of the game over time 
    def timerCallback(self):
        """Periodic timer callback invoked every ``loopTimeMS`` ms to drive bot turns and clocks."""
        self.runtime_ms += loopTimeMS
        # Take action
        match(self.timerState):
            # Nothing to do
            case "IDLE":
                # Look if its the bots turn
                if((self.gameLog.getLatestGame().turn == "w") and (self.whiteEngine != None)) or ((self.gameLog.getLatestGame().turn == "b") and (self.blackEngine != None)):
                    # Simulate a None user click to run the game
                    self.boardClick(None)
            case "ENGINE_RUNNING":
                # Engine is going, don't do anything
                None
            case "DRAW_WAIT":
                # This is used for drawing, go back to waiting
                self.timerState = "IDLE"              
            case _:
                None

        # Time control
        match(self.timeControlState):
            case "IDLE":
                self.writeMS(self.whiteMS,"w")
                self.writeMS(self.blackMS,"b")
            case "WHITE_DEC":
                self.whiteMS -= self.whiteTimeDecMS
                self.writeMS(self.whiteMS,"w")
                if(self.whiteMS <= 0):
                    self.whiteDisplay.append("White loses by time")
                    self.blackDisplay.append("Black wins by time") 
                    self.whiteMS = 0
                    self.timeControlState = "IDLE" 
                    self.timeoutCallback('w')
            case "BLACK_DEC":
                self.blackMS -= self.blackTimeDecMS
                self.writeMS(self.blackMS,"b")
                if(self.blackMS <= 0):
                    self.whiteDisplay.append("White wins by time")
                    self.blackDisplay.append("Black loses by time")  
                    self.blackMS = 0
                    self.timeControlState = "IDLE"
                    self.timeoutCallback('b')


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    window.show()
    timer = QTimer()
    timer.setInterval(loopTimeMS)
    timer.timeout.connect(window.timerCallback)
    timer.start()
    app.exec()
