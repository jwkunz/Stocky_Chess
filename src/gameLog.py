"""Move history log for storing and navigating sequential chess states."""

from chessState import chessState


class gameLog:
    """Maintains an ordered list of :class:`chessState.chessState` snapshots for a game.

    :ivar log: List of recorded board states in chronological order.
    :vartype log: list[chessState]
    """

    def __init__(self):
        """Initialize an empty game log."""
        self.log: list[chessState] = []

    def reset(self):
        """Reset the log to contain a single starting chess position."""
        cs = chessState()
        cs.setNewGame()
        self.log = [cs]

    def getGameByIndex(self, idx: int) -> chessState:
        """Retrieve the board state at a specific history index.

        :param idx: Index in the move history log.
        :type idx: int
        :return: The board state at ``idx``.
        :rtype: chessState
        """
        if not self.log:
            self.reset()
        clamped = max(0, min(idx, len(self.log) - 1))
        return self.log[clamped]

    def addState(self, cs: chessState):
        """Append a snapshot copy of a new board state to the end of the log.

        :param cs: The board state to append.
        :type cs: chessState
        """
        self.log.append(cs.copy())

    def currentGame(self) -> chessState:
        """Return the most recent board state in the log.

        :return: The latest board state.
        :rtype: chessState
        """
        if not self.log:
            self.reset()
        return self.log[-1]

    def getCurrentIndex(self) -> int:
        """Return the index of the latest board state in the log.

        :return: Index of the last element in :attr:`log`.
        :rtype: int
        """
        return max(0, len(self.log) - 1)

    def pruneAfterIndex(self, index: int):
        """Truncate all board states after the given index.

        :param index: The last history index to retain.
        :type index: int
        """
        if index < 0:
            return
        self.log = self.log[: index + 1]

    def getLatestGame(self) -> chessState:
        """Return the latest board state at the end of the log.

        :return: The last recorded board state.
        :rtype: chessState
        """
        return self.currentGame()
