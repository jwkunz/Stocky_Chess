from chessState import chessState
class gameLog:
    def __init__(self):
        self.log = []
    def reset(self):
        cs = chessState()
        cs.setNewGame()
        self.log = [cs]
    def getGameByIndex(self, idx : int):
        return self.log[idx]
    def addState(self, cs : chessState):
        self.log.append(cs)
    def currentGame(self):
        return self.log[-1]
    def getCurrentIndex(self):
        return len(self.log)-1
    def pruneAfterIndex(self,index : int):
        self.log = self.log[0:index+1]
    def getLatestGame(self):
        return self.log[-1]