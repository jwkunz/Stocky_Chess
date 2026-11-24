"""State machine for handling user board clicks and triggering engine moves."""

from chessBoard import chessBoard_widget
from chessState import player_t, chessState
from chessAdmin import (
    chessMove,
    convertLabel,
    getAllLegalMoves,
    getMovesFromSquare,
    hasKingCollision,
    isGameOver,
)
from gameLog import gameLog
from PyQt6.QtWidgets import QMainWindow
from uciEngine import uciEngine


class gameClickHandler:
    """Processes mouse clicks on the board and coordinates turn transitions and engine play.

    :ivar action_state: Current state of the turn/selection state machine
        (``'WHITE_SELECT_PIECE'``, ``'WHITE_SELECT_MOVE'``, ``'BLACK_SELECT_PIECE'``,
        ``'BLACK_SELECT_MOVE'``, ``'CHECKMATE'``, ``'STALEMATE'``, ``'TIMEOUT'``).
    :vartype action_state: str
    :ivar action_idx: Currently selected square index (0-63), or ``None`` when unselected.
    :vartype action_idx: int | None
    :ivar highlighed_moves: Currently highlighted legal moves for the selected piece.
    :vartype highlighed_moves: list[chessMove]
    """

    def __init__(self):
        """Initialize the click handler starting on White's piece selection."""
        self.action_state = "WHITE_SELECT_PIECE"
        self.action_idx: int | None = None
        self.highlighed_moves: list[chessMove] = []

    def setWhosTurn(self, whosMove: player_t):
        """Set the state machine to wait for piece selection by the specified player.

        :param whosMove: Player enum indicating whose turn it is.
        :type whosMove: player_t
        """
        self.action_idx = None
        self.highlighed_moves = []
        if whosMove == player_t.WHITE:
            self.action_state = "WHITE_SELECT_PIECE"
        else:
            self.action_state = "BLACK_SELECT_PIECE"

    def _updateGameEndState(self, cs: chessState, mainWindow: QMainWindow | None = None):
        """Evaluate whether ``cs`` has ended in checkmate or stalemate/draw and update state."""
        status = isGameOver(cs)
        if status == 0:
            self.action_state = "WHITE_SELECT_PIECE" if cs.turn == "w" else "BLACK_SELECT_PIECE"
        elif status == 1:
            self.action_state = "CHECKMATE"
            if mainWindow is not None:
                if cs.turn == "w":
                    mainWindow.whiteDisplay.append("White loses by checkmate")
                    mainWindow.blackDisplay.append("Black wins by checkmate")
                else:
                    mainWindow.whiteDisplay.append("White wins by checkmate")
                    mainWindow.blackDisplay.append("Black loses by checkmate")
        elif status == 2:
            self.action_state = "STALEMATE"
            if mainWindow is not None:
                mainWindow.whiteDisplay.append("Game ends in stalemate")
                mainWindow.blackDisplay.append("Game ends in stalemate")

    def _F1(self, idx: int, nextState: str, cs: chessState, cb: chessBoard_widget):
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
        moves = getMovesFromSquare(idx, cs, True)
        if len(moves) > 0:
            self.highlighed_moves = moves
            cb.renderBoard(cs, moves)
            self.action_idx = idx
            self.action_state = nextState
        else:
            self.highlighed_moves = []
            self.action_idx = None
            cb.renderBoard(cs)

    def _F2(
        self,
        idx: int,
        nextState: str,
        cs: chessState,
        cb: chessBoard_widget,
        gl: gameLog,
        mainWindow: QMainWindow,
    ):
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
        if not self.highlighed_moves:
            return

        pType = ""
        for m in self.highlighed_moves:
            if m.end == idx and m.promotionPiece != "":
                pType = mainWindow.promotionCallback(cs.pieceList[m.start].isupper())
                break

        for m in self.highlighed_moves:
            if m.end == idx and m.promotionPiece == pType:
                self.highlighed_moves = []
                self.action_idx = None
                mainWindow.movePieceWithAnimation(m, cs)
                gl.addState(cs)
                self._updateGameEndState(cs, mainWindow)
                cb.renderBoard(cs)
                return

    def _resolveEngineMove(self, bestMove: str | None, cs: chessState) -> chessMove | None:
        """Resolve a UCI move string (e.g. ``'e2e4'``) against legal moves in ``cs``.

        Falls back to the first legal move if ``bestMove`` is missing or invalid.

        :param bestMove: UCI coordinate move string from engine.
        :type bestMove: str | None
        :param cs: Current board state.
        :type cs: chessState
        :return: Matching legal :class:`chessAdmin.chessMove`, or ``None`` if game is over.
        :rtype: chessMove | None
        """
        legal_moves = getAllLegalMoves(cs)
        if not legal_moves:
            return None

        if bestMove and len(bestMove) >= 4:
            _, _, startIndex = convertLabel(bestMove[0:2])
            _, _, endIndex = convertLabel(bestMove[2:4])
            promotion = ""
            if len(bestMove) >= 5:
                promotion = bestMove[4].upper() if cs.turn == "w" else bestMove[4].lower()
            for candidate in legal_moves:
                if (
                    candidate.start == startIndex
                    and candidate.end == endIndex
                    and candidate.promotionPiece == promotion
                ):
                    return candidate

        return legal_moves[0]

    def applyEngineBestMove(
        self,
        bestMove: str | None,
        cs: chessState,
        cb: chessBoard_widget,
        gl: gameLog,
        mainWindow: QMainWindow,
    ):
        """Apply a resolved UCI move string to ``cs``, update ``gl``, and check for game end.

        :param bestMove: UCI coordinate move string (e.g. ``'e2e4'``) or ``None``.
        :type bestMove: str | None
        :param cs: Current chess state.
        :type cs: chessState
        :param cb: Chess board widget to render the updated state.
        :type cb: chessBoard_widget
        :param gl: Game log to append the resulting position.
        :type gl: gameLog
        :param mainWindow: Main window instance for timer updates and move narration.
        :type mainWindow: QMainWindow
        """
        if isGameOver(cs) != 0:
            self._updateGameEndState(cs, mainWindow)
            return

        selectedMove = self._resolveEngineMove(bestMove, cs)
        if selectedMove is None:
            self._updateGameEndState(cs, mainWindow)
            return

        self.highlighed_moves = []
        self.action_idx = None
        mainWindow.movePieceWithAnimation(selectedMove, cs)
        gl.addState(cs)
        self._updateGameEndState(cs, mainWindow)
        cb.renderBoard(cs)

    def engineHandler(
        self,
        engine: uciEngine,
        cs: chessState,
        cb: chessBoard_widget,
        gl: gameLog,
        mainWindow: QMainWindow,
    ):
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
        if isGameOver(cs) != 0:
            self._updateGameEndState(cs, mainWindow)
            return

        bestMove = engine.request_move(cs.getFENstring())
        self.applyEngineBestMove(bestMove, cs, cb, gl, mainWindow)

    def clickHandler(
        self,
        x: int | float | None,
        y: int | float | None,
        cs: chessState,
        cb: chessBoard_widget,
        gl: gameLog,
        mainWindow: QMainWindow,
    ):
        """Dispatch a user click at ``(x, y)`` or a bot turn (when coordinates are ``None``).

        Human clicks are ignored whenever the active side to move is controlled by an engine.

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
        if self.action_state in ("CHECKMATE", "STALEMATE", "TIMEOUT"):
            return

        is_bot_call = (x is None) or (y is None)
        if is_bot_call:
            if cs.turn == "w" and mainWindow.whiteEngine is not None:
                self.engineHandler(mainWindow.whiteEngine, cs, cb, gl, mainWindow)
            elif cs.turn == "b" and mainWindow.blackEngine is not None:
                self.engineHandler(mainWindow.blackEngine, cs, cb, gl, mainWindow)
            return

        # Human click: ignore if it is currently an engine's turn
        if (cs.turn == "w" and mainWindow.whiteEngine is not None) or (
            cs.turn == "b" and mainWindow.blackEngine is not None
        ):
            return

        idx = cb.coordToSquare(x, y)
        if idx < 0 or idx >= 64:
            return
        clickedPiece = cs.pieceList[idx]

        match self.action_state:
            case "WHITE_SELECT_PIECE":
                if clickedPiece is not None and clickedPiece.isupper():
                    self._F1(idx, "WHITE_SELECT_MOVE", cs, cb)

            case "WHITE_SELECT_MOVE":
                if idx == self.action_idx:
                    self.highlighed_moves = []
                    self.action_idx = None
                    cb.renderBoard(cs)
                    self.action_state = "WHITE_SELECT_PIECE"
                elif clickedPiece is not None and clickedPiece.isupper():
                    self._F1(idx, "WHITE_SELECT_MOVE", cs, cb)
                else:
                    self._F2(idx, "BLACK_SELECT_PIECE", cs, cb, gl, mainWindow)

            case "BLACK_SELECT_PIECE":
                if clickedPiece is not None and clickedPiece.islower():
                    self._F1(idx, "BLACK_SELECT_MOVE", cs, cb)

            case "BLACK_SELECT_MOVE":
                if idx == self.action_idx:
                    self.highlighed_moves = []
                    self.action_idx = None
                    cb.renderBoard(cs)
                    self.action_state = "BLACK_SELECT_PIECE"
                elif clickedPiece is not None and clickedPiece.islower():
                    self._F1(idx, "BLACK_SELECT_MOVE", cs, cb)
                else:
                    self._F2(idx, "WHITE_SELECT_PIECE", cs, cb, gl, mainWindow)
