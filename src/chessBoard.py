"""Chess board QLabel widget for rendering tiles, coordinates, pieces, and move highlights."""

from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtCore import Qt,QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen
import sys
from chessState import *
from chessAdmin import convertIndex


class board_color_t():
    """Color constants used for rendering board tiles and move highlight rings."""

    WHITE_TILE_COLOR = Qt.GlobalColor.white
    BLACK_TILE_COLOR = Qt.GlobalColor.darkGreen
    MOVE_TILE_COLOR = Qt.GlobalColor.blue
    CAPTURE_TILE_COLOR = Qt.GlobalColor.darkRed
    PROMOTION_TILE_COLOR = Qt.GlobalColor.green
    CHECK_TILE_COLOR = Qt.GlobalColor.darkYellow


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

    def __init__(self,length : int, borderTh : int, white_bottom = True):
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
        self.squareLength = (length - 2*borderTh) // 8
        self.spriteSheet = QImage("resources/ChessPieces")

    def _drawSquare(self, x :int ,y : int, length : int, color :  board_color_t, painter : QPainter):
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
        # Cache pevious brush 
        b = painter.brush()
        # Change color
        painter.setBrush(color)
        # Draw square
        painter.drawRect(x,y,length,length)
        # Return brush state
        painter.setBrush(b)
        return

    def _drawText(self, text : str, x :int ,y : int, length : int, color :  board_color_t, painter : QPainter):
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
        # Cache pevious brush 
        b = painter.pen()
        # Change color
        painter.setPen(color)
        # Draw square
        R = QRect(x,y,length,length)
        painter.drawText(R,Qt.AlignmentFlag.AlignCenter,text)
        # Return brush state
        painter.setPen(b)
        return

    def _drawPiece(self, x :int ,y : int, length : int, piece :  str, painter : QPainter):
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
        # Get sprite image
        I = self.spriteSheet
        s = int(length * 0.8)
        bx = int(x + (length-s)*0.5)
        by = int(y + (length-s)*0.5)

        # Get mask
        sprite_x = 0
        sprite_y = 0
        sprite_wx = 150
        sprite_wy = 150
        match(piece):
            case "P":
                sprite_x = 881
                sprite_wx = 940-sprite_x
                sprite_y = 170
                sprite_wy = 255-sprite_y
            case "N":
                sprite_x = 702
                sprite_wx = 780-sprite_x
                sprite_y = 170
                sprite_wy = 255-sprite_y        
            case "B":
                sprite_x = 531
                sprite_wx = 614-sprite_x
                sprite_y = 170
                sprite_wy = 255-sprite_y             
            case "R":
                sprite_x = 374
                sprite_wx = 439-sprite_x
                sprite_y = 170
                sprite_wy = 255-sprite_y                            
            case "Q":
                sprite_x = 191
                sprite_wx = 282-sprite_x
                sprite_y = 170
                sprite_wy = 255-sprite_y        
            case "K": 
                sprite_x = 30
                sprite_wx = 110-sprite_x
                sprite_y = 170
                sprite_wy = 255-sprite_y  
            case "p":
                sprite_x = 881
                sprite_wx = 940-sprite_x
                sprite_y = 25
                sprite_wy = 115-sprite_y
            case "n":
                sprite_x = 702
                sprite_wx = 780-sprite_x
                sprite_y = 25
                sprite_wy = 115-sprite_y        
            case "b":
                sprite_x = 531
                sprite_wx = 614-sprite_x
                sprite_y = 25
                sprite_wy = 115-sprite_y            
            case "r":
                sprite_x = 374
                sprite_wx = 439-sprite_x
                sprite_y = 25
                sprite_wy = 115-sprite_y                            
            case "q":
                sprite_x = 191
                sprite_wx = 282-sprite_x
                sprite_y = 25
                sprite_wy = 115-sprite_y
            case "k": 
                sprite_x = 30
                sprite_wx = 110-sprite_x
                sprite_y = 25
                sprite_wy = 115-sprite_y

        # Draw
        painter.drawImage(QRect(bx,by,s,s),I,QRect(sprite_x,sprite_y,sprite_wx,sprite_wy))
        return
                                      
    # Call this to put all the sprites on the pixmap
    # Render moves can be a list of available moves to draw (or None)
    def renderBoard(self, cs : chessState, highlightedMoves = []):
        """Render the full chess board, pieces, coordinates, and optional move highlights.

        :param cs: The board state to render.
        :type cs: chessState
        :param highlightedMoves: List of :class:`chessAdmin.chessMove` objects to highlight.
        :type highlightedMoves: list[chessMove]
        """
        canvas = QtGui.QPixmap(self.length,self.length)
        painter = QPainter(canvas)

        # Go through all columns and rows
        for i in range(8):
            for j in range(8):
                idx = i*8 + j

                # Checkerboard
                if((i+j) % 2 == 0):
                    color = board_color_t.WHITE_TILE_COLOR
                else:
                    color = board_color_t.BLACK_TILE_COLOR

                # Get square location
                x,y = self.index_to_xy(idx)
                
                # Draw square
                self._drawSquare(x,y,self.squareLength,color,painter)

                # Draw piece if necessary
                if(cs.pieceList[idx] != None):
                    self._drawPiece(x,y,self.squareLength,cs.pieceList[idx],painter)

        # Draw horizontal label
        for i in range(8):
            if(self.white_bottom):
                x,y  = self.index_to_xy(i)
            else:
                x,y  = self.index_to_xy(56+i)
            self._drawText(chr(i+65),x+self.squareLength*7//16,y-self.borderTh*2//3,self.squareLength//8,board_color_t.WHITE_TILE_COLOR,painter)
            self._drawText(chr(i+65),x+self.squareLength*7//16,y+self.squareLength*8+self.borderTh*3//16,self.squareLength//8,board_color_t.WHITE_TILE_COLOR,painter)
            if(self.white_bottom):
                x,y  = self.index_to_xy(i*8)
            else:
                x,y  = self.index_to_xy(i*8+7)
            self._drawText(chr((7-i)+49),x-self.borderTh*13//16,y+self.squareLength*7//16,self.squareLength//8,board_color_t.WHITE_TILE_COLOR,painter)
            self._drawText(chr((7-i)+49),x+self.squareLength*8+self.borderTh*7//16,y+self.squareLength*7//16,self.squareLength//8,board_color_t.WHITE_TILE_COLOR,painter)


        # Draw Highligted moves
        if(len(highlightedMoves) > 0):
            for m in highlightedMoves:
                og_pen = painter.pen()
                if(m.promotionPiece != ""):
                    painter.setPen(QPen(board_color_t.PROMOTION_TILE_COLOR,  15, Qt.PenStyle .SolidLine))  
                elif(m.is_capture):
                    painter.setPen(QPen(board_color_t.CAPTURE_TILE_COLOR,  15, Qt.PenStyle .SolidLine)) 
                elif(m.is_check):
                    painter.setPen(QPen(board_color_t.CHECK_TILE_COLOR,  15, Qt.PenStyle .SolidLine))                     
                else:
                    painter.setPen(QPen(board_color_t.MOVE_TILE_COLOR,  15, Qt.PenStyle .SolidLine))
                
                # Draw destination
                # Get square location
                x,y = self.index_to_xy(m.end)
                # Draw circle
                painter.drawArc(x,y,self.squareLength,self.squareLength,0*16,360*16)

                # Draw start
                painter.setPen(QPen(board_color_t.MOVE_TILE_COLOR,  15, Qt.PenStyle .SolidLine))
                # Get square location
                x,y = self.index_to_xy(m.start)
                # Draw circle
                painter.drawArc(x,y,self.squareLength,self.squareLength,0*16,360*16)

                painter.setPen(og_pen)
        painter.end()
        self.setPixmap(canvas)

    # Take pixel coordinates within the widget and return the square number
    def coordToSquare(self, x : int, y: int):
        """Convert widget pixel coordinates to a 0-63 board square index.

        :param x: Horizontal pixel coordinate.
        :type x: int
        :param y: Vertical pixel coordinate.
        :type y: int
        :return: Board index in the range 0..63 (or >=64 if outside the board).
        :rtype: int
        """
        col = round((x+self.squareLength/2) / self.squareLength) - 1
        row = round((y+self.squareLength/2) / self.squareLength) - 1
        if(self.white_bottom == False):
            row = 7 - row
            col = 7 - col
        return row*8 + col
               
    # Index XY
    def index_to_xy(self, index : int):
        """Convert a 0-63 board square index into top-left pixel coordinates on the canvas.

        :param index: Board square index (0..63).
        :type index: int
        :return: Tuple ``(x, y)`` of pixel coordinates.
        :rtype: tuple[int, int]
        """
        (j,i,label) = convertIndex(index)
        # Flip locations based on view state
        if(self.white_bottom):
            x = self.borderTh+j*self.squareLength   
            y = self.length - (self.borderTh+(i+1)*self.squareLength)
        else:
            x = self.length - (self.borderTh+(j+1)*self.squareLength)                                     
            y = self.borderTh+i*self.squareLength
        return (x,y)

if __name__ == "__main__":
    None
