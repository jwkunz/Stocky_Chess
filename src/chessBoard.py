"""Chess board QLabel widget for rendering tiles, coordinates, pieces, and move highlights."""

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen
from chessState import chessState
from chessAdmin import convertIndex, chessMove


class board_color_t:
    """Color constants used for rendering board tiles and move highlight rings."""

    WHITE_TILE_COLOR = Qt.GlobalColor.white
    BLACK_TILE_COLOR = Qt.GlobalColor.darkGreen
    MOVE_TILE_COLOR = Qt.GlobalColor.blue
    CAPTURE_TILE_COLOR = Qt.GlobalColor.darkRed
    PROMOTION_TILE_COLOR = Qt.GlobalColor.green
    CHECK_TILE_COLOR = Qt.GlobalColor.darkYellow


SPRITE_RECTS: dict[str, tuple[int, int, int, int]] = {
    "P": (881, 170, 940 - 881, 255 - 170),
    "N": (702, 170, 780 - 702, 255 - 170),
    "B": (531, 170, 614 - 531, 255 - 170),
    "R": (374, 170, 439 - 374, 255 - 170),
    "Q": (191, 170, 282 - 191, 255 - 170),
    "K": (30, 170, 110 - 30, 255 - 170),
    "p": (881, 25, 940 - 881, 115 - 25),
    "n": (702, 25, 780 - 702, 115 - 25),
    "b": (531, 25, 614 - 531, 115 - 25),
    "r": (374, 25, 439 - 374, 115 - 25),
    "q": (191, 25, 282 - 191, 115 - 25),
    "k": (30, 25, 110 - 30, 115 - 25),
}


class chessBoard_widget(QtWidgets.QLabel):
    """Custom QLabel widget that draws the chess board, piece sprites, and highlighted moves.

    :ivar length: Total pixel width and height of the square board widget.
    :vartype length: int
    :ivar borderTh: Pixel thickness of the coordinate border around the 8x8 grid.
    :vartype borderTh: int
    :ivar white_bottom: When ``True``, White is rendered at the bottom of the board.
    :vartype white_bottom: bool
    :ivar squareLength: Pixel width and height of an individual board square.
    :vartype squareLength: int
    """

    def __init__(self, length: int, borderTh: int, white_bottom: bool = True):
        """Initialize the chess board widget dimensions and orientation.

        :param length: Total width/height of the board widget in pixels.
        :type length: int
        :param borderTh: Border thickness in pixels.
        :type borderTh: int
        :param white_bottom: Whether White is displayed on the bottom ranks.
        :type white_bottom: bool
        """
        super().__init__()
        self.length = length
        self.borderTh = borderTh
        self.white_bottom = white_bottom
        self.squareLength = (length - 2 * borderTh) // 8
        self.spriteSheet = QImage("resources/ChessPieces")

    def _drawSquare(self, x: int, y: int, length: int, color, painter: QPainter):
        """Draw a single filled square on the board.

        :param x: Top-left X coordinate in pixels.
        :type x: int
        :param y: Top-left Y coordinate in pixels.
        :type y: int
        :param length: Side length of the square in pixels.
        :type length: int
        :param color: Fill color for the square.
        :type color: Qt.GlobalColor
        :param painter: Active QPainter instance.
        :type painter: QPainter
        """
        b = painter.brush()
        painter.setBrush(color)
        painter.drawRect(x, y, length, length)
        painter.setBrush(b)

    def _drawText(self, text: str, x: int, y: int, length: int, color, painter: QPainter):
        """Draw centered coordinate text within a bounding square.

        :param text: Text label to draw (e.g., file or rank character).
        :type text: str
        :param x: Top-left X coordinate in pixels.
        :type x: int
        :param y: Top-left Y coordinate in pixels.
        :type y: int
        :param length: Width and height of the text bounding box.
        :type length: int
        :param color: Pen color for the text.
        :type color: Qt.GlobalColor
        :param painter: Active QPainter instance.
        :type painter: QPainter
        """
        b = painter.pen()
        painter.setPen(color)
        painter.drawText(QRect(x, y, length, length), Qt.AlignmentFlag.AlignCenter, text)
        painter.setPen(b)

    def _drawPiece(self, x: int, y: int, length: int, piece: str, painter: QPainter):
        """Draw a chess piece sprite onto a board square.

        :param x: Top-left X coordinate of the square in pixels.
        :type x: int
        :param y: Top-left Y coordinate of the square in pixels.
        :type y: int
        :param length: Side length of the square in pixels.
        :type length: int
        :param piece: Single-character FEN piece identifier.
        :type piece: str
        :param painter: Active QPainter instance.
        :type painter: QPainter
        """
        rect = SPRITE_RECTS.get(piece)
        if rect is None:
            return
        s = int(length * 0.8)
        bx = int(x + (length - s) * 0.5)
        by = int(y + (length - s) * 0.5)
        sprite_x, sprite_y, sprite_wx, sprite_wy = rect
        painter.drawImage(
            QRect(bx, by, s, s),
            self.spriteSheet,
            QRect(sprite_x, sprite_y, sprite_wx, sprite_wy),
        )

    def renderBoard(self, cs: chessState, highlightedMoves: list[chessMove] | None = None):
        """Render the full chess board, pieces, coordinates, and optional move highlights.

        :param cs: The board state to render.
        :type cs: chessState
        :param highlightedMoves: List of :class:`chessAdmin.chessMove` objects to highlight.
        :type highlightedMoves: list[chessMove] | None
        """
        canvas = QtGui.QPixmap(self.length, self.length)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)

        for i in range(8):
            for j in range(8):
                idx = i * 8 + j
                color = (
                    board_color_t.WHITE_TILE_COLOR
                    if (i + j) % 2 == 0
                    else board_color_t.BLACK_TILE_COLOR
                )
                x, y = self.index_to_xy(idx)
                self._drawSquare(x, y, self.squareLength, color, painter)
                if cs.pieceList[idx] is not None:
                    self._drawPiece(x, y, self.squareLength, cs.pieceList[idx], painter)

        for i in range(8):
            x, y = self.index_to_xy(i if self.white_bottom else 56 + i)
            self._drawText(
                chr(i + 65),
                x + self.squareLength * 7 // 16,
                y - self.borderTh * 2 // 3,
                self.squareLength // 8,
                board_color_t.WHITE_TILE_COLOR,
                painter,
            )
            self._drawText(
                chr(i + 65),
                x + self.squareLength * 7 // 16,
                y + self.squareLength * 8 + self.borderTh * 3 // 16,
                self.squareLength // 8,
                board_color_t.WHITE_TILE_COLOR,
                painter,
            )
            x, y = self.index_to_xy(i * 8 if self.white_bottom else i * 8 + 7)
            self._drawText(
                chr((7 - i) + 49),
                x - self.borderTh * 13 // 16,
                y + self.squareLength * 7 // 16,
                self.squareLength // 8,
                board_color_t.WHITE_TILE_COLOR,
                painter,
            )
            self._drawText(
                chr((7 - i) + 49),
                x + self.squareLength * 8 + self.borderTh * 7 // 16,
                y + self.squareLength * 7 // 16,
                self.squareLength // 8,
                board_color_t.WHITE_TILE_COLOR,
                painter,
            )

        if highlightedMoves:
            for m in highlightedMoves:
                og_pen = painter.pen()
                if m.promotionPiece != "":
                    painter.setPen(QPen(board_color_t.PROMOTION_TILE_COLOR, 15, Qt.PenStyle.SolidLine))
                elif m.is_capture:
                    painter.setPen(QPen(board_color_t.CAPTURE_TILE_COLOR, 15, Qt.PenStyle.SolidLine))
                elif m.is_check:
                    painter.setPen(QPen(board_color_t.CHECK_TILE_COLOR, 15, Qt.PenStyle.SolidLine))
                else:
                    painter.setPen(QPen(board_color_t.MOVE_TILE_COLOR, 15, Qt.PenStyle.SolidLine))

                x, y = self.index_to_xy(m.end)
                painter.drawArc(x, y, self.squareLength, self.squareLength, 0, 360 * 16)

                painter.setPen(QPen(board_color_t.MOVE_TILE_COLOR, 15, Qt.PenStyle.SolidLine))
                x, y = self.index_to_xy(m.start)
                painter.drawArc(x, y, self.squareLength, self.squareLength, 0, 360 * 16)
                painter.setPen(og_pen)

        painter.end()
        self.setPixmap(canvas)

    def coordToSquare(self, x: int | float, y: int | float) -> int:
        """Convert widget pixel coordinates to a 0-63 board square index.

        :param x: Horizontal pixel coordinate.
        :type x: int | float
        :param y: Vertical pixel coordinate.
        :type y: int | float
        :return: Board index in the range 0..63 (or 64 if outside the board).
        :rtype: int
        """
        col = int((x - self.borderTh) // self.squareLength)
        row = int((y - self.borderTh) // self.squareLength)
        if col < 0 or col > 7 or row < 0 or row > 7:
            return 64
        if not self.white_bottom:
            row = 7 - row
            col = 7 - col
        return row * 8 + col

    def index_to_xy(self, index: int) -> tuple[int, int]:
        """Convert a 0-63 board square index into top-left pixel coordinates on the canvas.

        :param index: Board square index (0..63).
        :type index: int
        :return: Tuple ``(x, y)`` of pixel coordinates.
        :rtype: tuple[int, int]
        """
        j, i, _ = convertIndex(index)
        if self.white_bottom:
            x = self.borderTh + j * self.squareLength
            y = self.length - (self.borderTh + (i + 1) * self.squareLength)
        else:
            x = self.length - (self.borderTh + (j + 1) * self.squareLength)
            y = self.borderTh + i * self.squareLength
        return (x, y)
