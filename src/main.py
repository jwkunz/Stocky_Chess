"""Main PyQt6 application window, dialogs, chess clocks, and event loop for Stocky Chess."""

from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QRadioButton,
    QSpinBox,
    QCheckBox,
)
from PyQt6.QtCore import QTimer
from chessBoard import chessBoard_widget
from chessState import player_t, chessState
from gameClickHandler import gameClickHandler
from gameLog import gameLog
from chessAdmin import (
    chessMove,
    movePiece,
    convertIndex,
    getPieceTextNameOn,
    getPiecetoTextName,
    hasKingCollision,
)
from uciEngine import uciEngine
import sys
import time

loopTimeMS = 100


class Ui(QtWidgets.QMainWindow):
    """Main window controller for the Stocky Chess desktop application.

    Loads the Qt Designer UI from ``resources/StockyChess.ui``, initializes the
    board widget, manages player types (Human or Stockfish), runs the chess clocks,
    and coordinates user and engine moves.

    :cvar version: Application version string.
    :vartype version: str
    """

    version = "2.0.4"

    def __init__(self):
        """Initialize the main window, board widget, signal connections, and default game state."""
        super(Ui, self).__init__()
        uic.loadUi("resources/StockyChess.ui", self)

        S = QtWidgets.QGraphicsScene()
        self.viewport.setScene(S)
        self.viewport.show()

        self.chessBoardWidget = chessBoard_widget(
            self.viewport.width(), self.viewport.width() // 40, True
        )
        self.gameClickHandler = gameClickHandler()

        self.whiteEngine: uciEngine | None = None
        self.blackEngine: uciEngine | None = None
        self.botPaused: bool = True
        self._in_board_click: bool = False

        self.startNewGame()

        self.print_to_console(f"Welcome to Stocky Chess Version {self.version}")
        self.print_to_console("Select Menu >> New Game to begin")

        self.FENhistory: list[str] = []
        self.render()

        S.mouseReleaseEvent = lambda event: self.boardClick(event)
        self.actionWhite_Bottom.triggered.connect(lambda: self.setBoardDirection(True))
        self.actionBlack_Bottom.triggered.connect(lambda: self.setBoardDirection(False))
        self.actionNew_Game.triggered.connect(self.startNewGame)
        self.actionSetWhite_Human.triggered.connect(lambda: self.setHuman("w"))
        self.actionSetBlack_Human.triggered.connect(lambda: self.setHuman("b"))
        self.actionSetWhite_Stockfish.triggered.connect(lambda: self.setStockfish("w"))
        self.actionSetBlack_Stockfish.triggered.connect(lambda: self.setStockfish("b"))
        self.actionSetWhiteTimeControlMode.triggered.connect(lambda: self.setTimeControlMode("w"))
        self.actionSetBlackTimeControlMode.triggered.connect(lambda: self.setTimeControlMode("b"))
        self.actionImport_FEN.triggered.connect(self.setFENstate)
        if hasattr(self, "actionStart_Pause_Bot"):
            self.actionStart_Pause_Bot.triggered.connect(self.toggleBotPause)
        if hasattr(self, "botPauseButton"):
            self.botPauseButton.pressed.connect(self.toggleBotPause)
        self.prevMove.pressed.connect(self.setPrevMove)
        self.nextMove.pressed.connect(self.setNextMove)

        self.setHuman("w")
        self.setHuman("b")

        self.runtime_ms = 0
        self.timerState = "IDLE"
        self.loopTimeMS = loopTimeMS

    def setTimeControlMode(self, color: str):
        """Open a modal dialog to configure initial clock time and increment for a player.

        :param color: Player color code (``'w'`` or ``'b'``).
        :type color: str
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Enter Time For White:" if color == "w" else "Enter Time For Black:")
        dlg.layout = QVBoxLayout()

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
        hLayout.addWidget(QLabel("seconds"))
        it_sc = QSpinBox()
        it_sc.setMaximum(59)
        it_sc.setMinimum(0)
        it_sc.setValue(0)
        hLayout.addWidget(it_sc)
        dlg.layout.addLayout(hLayout)

        hLayout = QHBoxLayout()
        hLayout.addWidget(QLabel("Move Increment (seconds)"))
        inc_s = QSpinBox()
        inc_s.setMaximum(59)
        inc_s.setMinimum(0)
        inc_s.setValue(0)
        hLayout.addWidget(inc_s)
        dlg.layout.addLayout(hLayout)

        hLayout = QHBoxLayout()
        noTime = QCheckBox("No Time Control")
        hLayout.addWidget(noTime)
        bothPlayers = QCheckBox("Set Both Players")
        hLayout.addWidget(bothPlayers)
        dlg.layout.addLayout(hLayout)

        def apply():
            if noTime.isChecked():
                timeMS = 100 * 60 * 60 * 1000 - 1
                incMS = 0
                timeDecMS = 0
            else:
                timeMS = (
                    60 * 60 * 1000 * it_hr.value()
                    + 60 * 1000 * it_mn.value()
                    + 1000 * it_sc.value()
                )
                incMS = 1000 * inc_s.value()
                timeDecMS = loopTimeMS
            if color == "w" or bothPlayers.isChecked():
                self.whiteMS = timeMS
                self.whiteTimeIncMS = incMS
                self.whiteTimeDecMS = timeDecMS
            if color == "b" or bothPlayers.isChecked():
                self.blackMS = timeMS
                self.blackTimeIncMS = incMS
                self.blackTimeDecMS = timeDecMS
            dlg.close()

        applyButton = QPushButton("Apply")
        applyButton.pressed.connect(apply)
        dlg.layout.addWidget(applyButton)
        dlg.setLayout(dlg.layout)
        dlg.exec()

    def setBoardDirection(self, direction: bool):
        """Set the board orientation and re-render.

        :param direction: ``True`` for White at the bottom, ``False`` for Black at the bottom.
        :type direction: bool
        """
        self.chessBoardWidget.white_bottom = direction
        self.render()

    def setHuman(self, color: str):
        """Configure the specified side to be controlled by a human player.

        :param color: Player color code (``'w'`` or ``'b'``).
        :type color: str
        """
        if color == "w":
            if getattr(self, "whiteEngine", None) is not None:
                self.whiteEngine.close()
            self.whiteEngine = None
            self.whiteType.setText("HUMAN")
        else:
            if getattr(self, "blackEngine", None) is not None:
                self.blackEngine.close()
            self.blackEngine = None
            self.blackType.setText("HUMAN")

    def setStockfish(self, color: str):
        """Open a dialog to configure Stockfish skill level and depth for the given side.

        :param color: Player color code (``'w'`` or ``'b'``).
        :type color: str
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Stockfish:")
        dlg.layout = QVBoxLayout()

        dlg.layout.addWidget(QLabel("Select Difficulty:"))
        diffDial = QSpinBox()
        diffDial.setMaximum(20)
        diffDial.setMinimum(1)
        diffDial.setValue(10)
        dlg.layout.addWidget(diffDial)

        dlg.layout.addWidget(QLabel("Select Search Depth:"))
        depthDial = QSpinBox()
        depthDial.setMaximum(30)
        depthDial.setMinimum(1)
        depthDial.setValue(20)
        dlg.layout.addWidget(depthDial)

        button = QPushButton("Accept")
        dlg.layout.addWidget(button)
        button.pressed.connect(lambda: dlg.close())

        dlg.setLayout(dlg.layout)
        dlg.exec()

        difficulty = diffDial.value()
        moveDepth = depthDial.value()

        try:
            newEngine = uciEngine(difficulty=difficulty, moveDepth=moveDepth)
        except (OSError, RuntimeError) as exc:
            self.print_to_console(f"Failed to start Stockfish engine: {exc}")
            return

        if color == "w":
            if getattr(self, "whiteEngine", None) is not None:
                self.whiteEngine.close()
            self.whiteEngine = newEngine
            self.whiteType.setText(f"STOCKFISH LVL {difficulty} DEPTH {moveDepth}")
        else:
            if getattr(self, "blackEngine", None) is not None:
                self.blackEngine.close()
            self.blackEngine = newEngine
            self.blackType.setText(f"STOCKFISH LVL {difficulty} DEPTH {moveDepth}")
        self.setBotPaused(True)

    def setBotPaused(self, paused: bool):
        """Set the bot pause state and update the Start/Pause button label.

        :param paused: ``True`` to pause engine play, ``False`` to allow engine play.
        :type paused: bool
        """
        self.botPaused = paused
        if hasattr(self, "botPauseButton"):
            self.botPauseButton.setText("START BOT" if self.botPaused else "PAUSE BOT")

    def toggleBotPause(self):
        """Toggle the engine start/pause state."""
        self.setBotPaused(not self.botPaused)

    def closeEvent(self, event):
        """Cleanly shut down any active Stockfish subprocesses when the window closes."""
        if getattr(self, "whiteEngine", None) is not None:
            self.whiteEngine.close()
        if getattr(self, "blackEngine", None) is not None:
            self.blackEngine.close()
        super().closeEvent(event)

    def render(self, updateBoard: bool = True):
        """Refresh the board display, FEN bar, turn slider, and material counts.

        :param updateBoard: When ``True``, redraws the board pixmap before updating the scene.
        :type updateBoard: bool
        """
        renderGame = self.gameLog.getGameByIndex(self.gameRenderIndex)
        if updateBoard:
            self.chessBoardWidget.renderBoard(renderGame)
        self.FENbar.setText(renderGame.getFENstring())
        self.viewport.scene().clear()
        self.viewport.scene().addPixmap(self.chessBoardWidget.pixmap())
        self.update_move_slider(renderGame.turn)
        self.updateMaterial()
        self.repaint()

    def startNewGame(self):
        """Reset the game log, click state machine, and clocks for a new game."""
        self.gameLog = gameLog()
        self.gameLog.reset()
        self.gameRenderIndex = 0
        self.gameClickHandler.setWhosTurn(player_t.WHITE)
        self.timerState = "IDLE"
        self._in_board_click = False
        self.timeControlState = "IDLE"
        self.whiteMS = 100 * 60 * 60 * 1000 - 1
        self.blackMS = 100 * 60 * 60 * 1000 - 1
        self.whiteTimeIncMS = 0
        self.blackTimeIncMS = 0
        self.whiteTimeDecMS = 0
        self.blackTimeDecMS = 0
        self.render()

    def updateMaterial(self):
        """Compute and display active material and point balance for White and Black."""
        piece_values = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}
        order_rank = {"P": 0, "N": 1, "B": 2, "R": 3, "Q": 4, "K": 5}

        white_pieces: list[str] = []
        black_pieces: list[str] = []
        white_score = 0
        black_score = 0

        for p in self.gameLog.getGameByIndex(self.gameRenderIndex).pieceList:
            if p is None:
                continue
            if p.isupper():
                white_pieces.append(p)
                white_score += piece_values.get(p, 0)
            else:
                black_pieces.append(p)
                black_score += piece_values.get(p.upper(), 0)

        white_str = "".join(sorted(white_pieces, key=lambda c: order_rank.get(c, 99)))
        black_str = "".join(sorted(black_pieces, key=lambda c: order_rank.get(c.upper(), 99)))

        balance = white_score - black_score
        if balance > 0:
            self.materialWhite.setText(f"{white_str}   (+{balance})")
            self.materialBlack.setText(black_str)
        elif balance < 0:
            self.materialWhite.setText(white_str)
            self.materialBlack.setText(f"(+{-balance})   {black_str}")
        else:
            self.materialWhite.setText(white_str)
            self.materialBlack.setText(black_str)

    def update_move_slider(self, turn: str):
        """Update the UI turn indicator slider based on whose turn it is.

        :param turn: ``'w'`` for White or ``'b'`` for Black.
        :type turn: str
        """
        self.moveSlider.setValue(1 if turn == "b" else 0)

    def print_to_console(self, s: str):
        """Append a message line to the shared console widget.

        :param s: Message text to append.
        :type s: str
        """
        self.printConsole.append(s)

    def movePieceWithAnimation(self, move: chessMove, cs: chessState, filterForCheck: bool = True):
        """Log move narration, update player clocks, and apply the move to ``cs``.

        :param move: Move descriptor to execute.
        :type move: chessMove
        :param cs: Board state to mutate.
        :type cs: chessState
        :param filterForCheck: Passed through to :func:`chessAdmin.movePiece`.
        :type filterForCheck: bool
        """
        moving_turn = cs.turn
        move_number = cs.full_move
        _, _, startLabel = convertIndex(move.start)
        startPieceRaw = getPieceTextNameOn(move.start, cs)
        startPieceName = startPieceRaw.capitalize() if startPieceRaw else "Piece"

        _, _, endLabel = convertIndex(move.end)
        endPieceName = getPieceTextNameOn(move.end, cs)
        if endPieceName is not None:
            endLabel = f"capture {endPieceName} on {endLabel}"

        enPassantText = " and captured with en passant" if (move.enpassantFlag and move.is_capture) else ""
        moveText = "castles" if len(move.castleRookSquares) > 0 else "moves"

        promoteText = ""
        if move.promotionPiece != "":
            name = getPiecetoTextName(move.promotionPiece)
            promoteText = f" and promote to {name}"

        movePiece(move, cs, filterForCheck)
        delivers_check = move.is_check or hasKingCollision(cs)
        checkText = " for check" if delivers_check else ""

        narration = f"{move_number}. {startPieceName} {moveText} from {startLabel} to {endLabel}{enPassantText}{promoteText}{checkText}."
        if moving_turn == "w":
            self.whiteDisplay.append(narration)
            self.whiteMS += self.whiteTimeIncMS
            self.writeMS(self.whiteMS, "w")
            self.timeControlState = "BLACK_DEC"
        else:
            self.blackDisplay.append(narration)
            self.blackMS += self.blackTimeIncMS
            self.writeMS(self.blackMS, "b")
            self.timeControlState = "WHITE_DEC"

    def boardClick(self, event):
        """Handle a mouse release event on the board scene or trigger an engine move when ``event`` is ``None``.

        Guarded against re-entrant execution so clicks or timer ticks during an engine
        computation never corrupt state.

        :param event: QGraphicsSceneMouseEvent for human clicks, or ``None`` for engine turns.
        :type event: QtWidgets.QGraphicsSceneMouseEvent | None
        """
        if self._in_board_click:
            return
        if self.gameClickHandler.action_state in ("CHECKMATE", "STALEMATE", "TIMEOUT"):
            return

        self._in_board_click = True
        try:
            tempLog = gameLog()
            tempLog.log = [state.copy() for state in self.gameLog.log[: self.gameRenderIndex + 1]]
            tempGame = tempLog.currentGame().copy()

            if event is not None:
                self.gameClickHandler.clickHandler(
                    event.scenePos().x(),
                    event.scenePos().y(),
                    tempGame,
                    self.chessBoardWidget,
                    tempLog,
                    self,
                )
            else:
                self.timerState = "ENGINE_RUNNING"
                t0 = time.monotonic()
                self.gameClickHandler.clickHandler(
                    None, None, tempGame, self.chessBoardWidget, tempLog, self
                )
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                if self.timeControlState == "BLACK_DEC" and self.whiteTimeDecMS > 0:
                    self.whiteMS = max(0, self.whiteMS - elapsed_ms)
                elif self.timeControlState == "WHITE_DEC" and self.blackTimeDecMS > 0:
                    self.blackMS = max(0, self.blackMS - elapsed_ms)

            if len(tempLog.log) > self.gameRenderIndex + 1:
                self.gameLog = tempLog
                self.gameRenderIndex = self.gameLog.getCurrentIndex()

            self.render(False)

            if self.gameClickHandler.action_state == "CHECKMATE":
                self.timeControlState = "IDLE"
                self.timerState = "GAME_OVER"
                self.checkmateCallback()
                return
            if self.gameClickHandler.action_state == "STALEMATE":
                self.timeControlState = "IDLE"
                self.timerState = "GAME_OVER"
                self.stalemateCallback()
                return

            self.timerState = "DRAW_WAIT"
        finally:
            self._in_board_click = False

    def checkmateCallback(self):
        """Display a modal notification dialog announcing checkmate."""
        dlg = QDialog(self)
        dlg.setWindowTitle(" ")
        dlg.layout = QVBoxLayout()
        dlg.layout.addWidget(QLabel("Checkmate!"))
        dlg.setLayout(dlg.layout)
        dlg.exec()

    def stalemateCallback(self):
        """Display a modal notification dialog announcing stalemate."""
        dlg = QDialog(self)
        dlg.setWindowTitle(" ")
        dlg.layout = QVBoxLayout()
        dlg.layout.addWidget(QLabel("Stalemate!"))
        dlg.setLayout(dlg.layout)
        dlg.exec()

    def timeoutCallback(self, color: str):
        """Transition the game to ``TIMEOUT`` and display an out-of-time dialog.

        :param color: Player color that ran out of time (``'w'`` or ``'b'``).
        :type color: str
        """
        self.gameClickHandler.action_state = "TIMEOUT"
        self.timerState = "GAME_OVER"
        dlg = QDialog(self)
        dlg.setWindowTitle(" ")
        dlg.layout = QVBoxLayout()
        dlg.layout.addWidget(QLabel("Out of time!"))
        dlg.setLayout(dlg.layout)
        dlg.exec()

    def promotionCallback(self, is_white: bool) -> str:
        """Display a modal dialog prompting the player to choose a pawn promotion piece.

        :param is_white: ``True`` if the promoting player is White, ``False`` for Black.
        :type is_white: bool
        :return: Single-character FEN symbol for the chosen promotion piece.
        :rtype: str
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Select a promotion piece:")
        dlg.layout = QVBoxLayout()

        buttonGroup_layout = QHBoxLayout()
        promotion_group = QtWidgets.QButtonGroup(dlg)
        for idx_btn, label in enumerate(("Queen", "Rook", "Bishop", "Knight")):
            rb = QRadioButton(label)
            promotion_group.addButton(rb, idx_btn)
            if idx_btn == 0:
                rb.setChecked(True)
            buttonGroup_layout.addWidget(rb)

        button = QPushButton("Apply")

        def apply():
            mapping = {0: "q", 1: "r", 2: "b", 3: "n"}
            val = mapping.get(promotion_group.checkedId(), "q")
            dlg.done(ord(val.upper() if is_white else val.lower()))

        button.pressed.connect(apply)
        dlg.layout.addLayout(buttonGroup_layout)
        dlg.layout.addWidget(button)
        dlg.setLayout(dlg.layout)

        code = dlg.exec()
        if code == 0:
            return "Q" if is_white else "q"
        return chr(code)

    def setFENstate(self):
        """Open a dialog allowing the user to paste and load a custom FEN string."""
        dlg = QDialog(self)
        dlg.setWindowTitle("FEN Import")
        dlg.layout = QVBoxLayout()
        message = QLabel("Paste in a FEN String")
        text = QTextEdit()
        button = QPushButton("Apply")

        def update():
            FENstr = text.toPlainText().strip()
            try:
                testState = chessState()
                testState.setFENstring(FENstr)
            except ValueError as exc:
                self.print_to_console(f"Invalid FEN string: {exc}")
                return
            self.startNewGame()
            self.gameLog.log[self.gameRenderIndex].setFENstring(FENstr)
            self.gameClickHandler.setWhosTurn(
                player_t.WHITE if self.gameLog.currentGame().turn == "w" else player_t.BLACK
            )
            self.render(True)
            dlg.close()

        button.pressed.connect(update)
        dlg.layout.addWidget(message)
        dlg.layout.addWidget(text)
        dlg.layout.addWidget(button)
        dlg.setLayout(dlg.layout)
        dlg.exec()

    def setPrevMove(self):
        """Step backward one ply in the move history log and re-render the board."""
        if self.gameRenderIndex <= 0:
            self.gameRenderIndex = 0
            return
        self.gameRenderIndex -= 1
        rendered = self.gameLog.getGameByIndex(self.gameRenderIndex)
        self.gameClickHandler.setWhosTurn(
            player_t.WHITE if rendered.turn == "w" else player_t.BLACK
        )
        self.render(True)

    def setNextMove(self):
        """Step forward one ply in the move history log and re-render the board."""
        if self.gameRenderIndex >= self.gameLog.getCurrentIndex():
            self.gameRenderIndex = self.gameLog.getCurrentIndex()
            return
        self.gameRenderIndex += 1
        rendered = self.gameLog.getGameByIndex(self.gameRenderIndex)
        self.gameClickHandler.setWhosTurn(
            player_t.WHITE if rendered.turn == "w" else player_t.BLACK
        )
        self.render(True)

    def writeMS(self, ms: int, turn: str):
        """Format a millisecond duration as ``HH:MM:SS.d`` and display it on the player's clock.

        :param ms: Remaining time in milliseconds.
        :type ms: int
        :param turn: ``'w'`` for White's clock or ``'b'`` for Black's clock.
        :type turn: str
        """
        clamped = max(0, ms)
        hours = clamped // (1000 * 60 * 60)
        minutes = (clamped // (1000 * 60)) % 60
        seconds = (clamped // 1000) % 60
        tenths = (clamped % 1000) // 100
        line = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{tenths:01d}"
        if turn == "w":
            self.whiteTime.setText(line)
        else:
            self.blackTime.setText(line)

    def timerCallback(self):
        """Periodic timer callback invoked every ``loopTimeMS`` ms to drive bot turns and clocks."""
        if self._in_board_click:
            return

        self.runtime_ms += loopTimeMS
        match self.timerState:
            case "IDLE":
                if not self.botPaused and self.gameClickHandler.action_state not in (
                    "CHECKMATE",
                    "STALEMATE",
                    "TIMEOUT",
                ):
                    active = self.gameLog.getGameByIndex(self.gameRenderIndex)
                    if (active.turn == "w" and self.whiteEngine is not None) or (
                        active.turn == "b" and self.blackEngine is not None
                    ):
                        self.boardClick(None)
            case "ENGINE_RUNNING":
                pass
            case "DRAW_WAIT":
                self.timerState = "IDLE"
            case _:
                pass

        match self.timeControlState:
            case "IDLE":
                self.writeMS(self.whiteMS, "w")
                self.writeMS(self.blackMS, "b")
            case "WHITE_DEC":
                self.whiteMS -= self.whiteTimeDecMS
                self.writeMS(self.whiteMS, "w")
                if self.whiteMS <= 0:
                    self.whiteDisplay.append("White loses by time")
                    self.blackDisplay.append("Black wins by time")
                    self.whiteMS = 0
                    self.timeControlState = "IDLE"
                    self.timeoutCallback("w")
            case "BLACK_DEC":
                self.blackMS -= self.blackTimeDecMS
                self.writeMS(self.blackMS, "b")
                if self.blackMS <= 0:
                    self.whiteDisplay.append("White wins by time")
                    self.blackDisplay.append("Black loses by time")
                    self.blackMS = 0
                    self.timeControlState = "IDLE"
                    self.timeoutCallback("b")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    window.show()
    timer = QTimer()
    timer.setInterval(loopTimeMS)
    timer.timeout.connect(window.timerCallback)
    timer.start()
    app.exec()
