from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtCore import Qt,QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen
import sys
from chessState import *
from chessAdmin import convertIndex

class board_color_t():
    WHITE_TILE_COLOR = Qt.GlobalColor.white
    BLACK_TILE_COLOR = Qt.GlobalColor.darkGreen
    MOVE_TILE_COLOR = Qt.GlobalColor.blue
    CAPTURE_TILE_COLOR = Qt.GlobalColor.darkRed
    PROMOTION_TILE_COLOR = Qt.GlobalColor.green
    CHECK_TILE_COLOR = Qt.GlobalColor.darkYellow
        
class chessBoard_widget(QtWidgets.QLabel):
    def __init__(self,length : int, borderTh : int, white_bottom = True):
        super().__init__()
        self.length = length
        self.borderTh = borderTh  
        self.white_bottom = white_bottom    
        self.squareLength = (length - 2*borderTh) // 8

    def _drawSquare(self, x :int ,y : int, length : int, color :  board_color_t, painter : QPainter):
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
        # Get sprite image
        I = QImage("resources/ChessPieces")
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
        col = round((x+self.squareLength/2) / self.squareLength) - 1
        row = round((y+self.squareLength/2) / self.squareLength) - 1
        if(self.white_bottom == False):
            row = 7 - row
            col = 7 - col
        return row*8 + col
               
    # Index XY
    def index_to_xy(self, index : int):
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
    

