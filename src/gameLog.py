"""Move history log for storing and navigating sequential chess states."""

from chessState import chessState


class gameLog:
    """Maintains an ordered list of :class:`chessState.chessState` snapshots for a game.

    :ivar log: List of recorded board states in chronological order.
    :vartype log: list[chessState]
    """

    def __init__(self):
        """Initialize an empty game log."""
        self.log = []

    def reset(self):
        """Reset the log to contain a single starting chess position."""
        cs = chessState()
        cs.setNewGame()
        self.log = [cs]

    def getGameByIndex(self, idx : int):
        """Retrieve the board state at a specific history index.

        :param idx: Index in the move history log.
        :type idx: int
        :return: The board state at ``idx``.
        :rtype: chessState
        """
        return self.log[idx]

    def addState(self, cs : chessState):
        """Append a new board state to the end of the log.

        :param cs: The board state to append.
        :type cs: chessState
        """
        self.log.append(cs)

    def currentGame(self):
        """Return the most recent board state in the log.

        :return: The latest board state.
        :rtype: chessState
        """
        return self.log[-1]

    def getCurrentIndex(self):
        """Return the index of the latest board state in the log.

        :return: Index of the last element in :attr:`log`.
        :rtype: int
        """
        return len(self.log)-1

    def pruneAfterIndex(self,index : int):
        """Truncate all board states after the given index.

        :param index: The last history index to retain.
        :type index: int
        """
        self.log = self.log[0:index+1]

    def getLatestGame(self):
        """Return the latest board state at the end of the log.

        :return: The last recorded board state.
        :rtype: chessState
        """
        return self.log[-1]
