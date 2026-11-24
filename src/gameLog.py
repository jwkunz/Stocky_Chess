"""Move history log for storing, navigating, and exporting sequential chess states."""

from datetime import date
from chessState import chessState, START_FEN
from chessAdmin import inferMoveBetweenStates, isGameOver, moveToSAN


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

    def isThreefoldRepetition(self, up_to_index: int | None = None) -> bool:
        """Return ``True`` if the position at ``up_to_index`` (or latest) has occurred at least 3 times.

        :param up_to_index: Optional last index in :attr:`log` to include.
        :type up_to_index: int | None
        :return: ``True`` if threefold repetition is reached.
        :rtype: bool
        """
        if not self.log:
            return False
        end_idx = len(self.log) - 1 if up_to_index is None else min(up_to_index, len(self.log) - 1)
        if end_idx < 0:
            return False
        sub_log = self.log[: end_idx + 1]
        target_key = sub_log[-1].getPositionKey()
        return sum(1 for state in sub_log if state.getPositionKey() == target_key) >= 3

    def toPGN(
        self,
        white_name: str = "White",
        black_name: str = "Black",
        event: str = "Stocky Chess Game",
        site: str = "Local",
        game_date: str | None = None,
        result: str | None = None,
        up_to_index: int | None = None,
    ) -> str:
        """Serialize the recorded game history into Portable Game Notation (PGN).

        Includes standard Seven Tag Roster headers, optional ``SetUp`` and ``FEN``
        headers when starting from a custom position, Standard Algebraic Notation (SAN)
        move text, and the game result token.

        :param white_name: Name of the White player.
        :type white_name: str
        :param black_name: Name of the Black player.
        :type black_name: str
        :param event: PGN Event tag value.
        :type event: str
        :param site: PGN Site tag value.
        :type site: str
        :param game_date: Date in ``YYYY.MM.DD`` format (defaults to today).
        :type game_date: str | None
        :param result: Explicit PGN result (``'1-0'``, ``'0-1'``, ``'1/2-1/2'``, ``'*'``),
            or ``None`` to infer from the final position.
        :type result: str | None
        :param up_to_index: Optional final history index to export.
        :type up_to_index: int | None
        :return: Complete PGN string.
        :rtype: str
        """
        if not self.log:
            self.reset()

        end_idx = len(self.log) - 1 if up_to_index is None else max(0, min(up_to_index, len(self.log) - 1))
        states = self.log[: end_idx + 1]
        final_state = states[-1]

        if result is None:
            status = isGameOver(final_state, states)
            if status == 1:
                result = "0-1" if final_state.turn == "w" else "1-0"
            elif status == 2:
                result = "1/2-1/2"
            else:
                result = "*"

        date_str = game_date or date.today().strftime("%Y.%m.%d")
        headers = [
            f'[Event "{event}"]',
            f'[Site "{site}"]',
            f'[Date "{date_str}"]',
            '[Round "1"]',
            f'[White "{white_name}"]',
            f'[Black "{black_name}"]',
            f'[Result "{result}"]',
        ]

        initial_fen = states[0].getFENstring()
        if initial_fen != START_FEN:
            headers.append('[SetUp "1"]')
            headers.append(f'[FEN "{initial_fen}"]')

        tokens: list[str] = []
        for i in range(len(states) - 1):
            prev_s = states[i]
            next_s = states[i + 1]
            move = inferMoveBetweenStates(prev_s, next_s)
            if move is None:
                break
            san = moveToSAN(move, prev_s, states[: i + 1])
            if prev_s.turn == "w":
                tokens.append(f"{prev_s.full_move}. {san}")
            else:
                if i == 0:
                    tokens.append(f"{prev_s.full_move}... {san}")
                else:
                    tokens.append(san)

        tokens.append(result)
        movetext = " ".join(tokens)
        return "\n".join(headers) + "\n\n" + movetext + "\n"
