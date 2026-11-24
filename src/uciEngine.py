"""UCI engine wrapper for communicating with a Stockfish subprocess."""

import os
import shutil
import subprocess


def resolve_stockfish_path(path: str | None = None) -> str:
    """Resolve the path to a Stockfish executable across platforms.

    :param path: Explicit path or binary name, or ``None`` to auto-detect.
    :type path: str | None
    :return: Resolved executable path or fallback binary name.
    :rtype: str
    """
    if path:
        resolved = shutil.which(path) or (path if os.path.isfile(path) else None)
        if resolved:
            return resolved
    for candidate in ("stockfish", "stockfish.exe", "./stockfish", "./stockfish.exe"):
        resolved = shutil.which(candidate) or (candidate if os.path.isfile(candidate) else None)
        if resolved:
            return resolved
    return path if path else ("stockfish.exe" if os.name == "nt" else "stockfish")


class uciEngine:
    """Manages a Stockfish engine subprocess via the Universal Chess Interface (UCI) protocol.

    :ivar stockfish_process: The underlying Stockfish Popen process.
    :vartype stockfish_process: subprocess.Popen | None
    :ivar current_state: Current state in the UCI handshake/search state machine.
    :vartype current_state: str
    :ivar difficulty: Configured Stockfish Skill Level (0-20).
    :vartype difficulty: int
    :ivar depth: Search depth passed to ``go depth``.
    :vartype depth: int
    :ivar inputFEN: Last FEN position requested for engine evaluation.
    :vartype inputFEN: str
    """

    def __init__(self, path: str | None = None, difficulty: int = 20, moveDepth: int = 20):
        """Launch Stockfish and run the UCI initialization state machine until ready.

        :param path: Path to the Stockfish executable. Defaults to auto-detecting
            ``stockfish`` or ``stockfish.exe`` on PATH or in the working directory.
        :type path: str | None
        :param difficulty: Stockfish Skill Level (0 to 20).
        :type difficulty: int
        :param moveDepth: Search depth in plies.
        :type moveDepth: int
        """
        resolved_path = resolve_stockfish_path(path)
        self.stockfish_process = subprocess.Popen(
            [resolved_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.current_state = "START_UCI"
        self.difficulty = max(0, min(20, int(difficulty)))
        self.depth = max(1, int(moveDepth))
        self.inputFEN = ""
        self.cpu_white = False

        while self.current_state not in ("WAITING", "DONE"):
            self.tick()
        if self.current_state == "DONE":
            self.close()
            raise RuntimeError("Stockfish process exited unexpectedly during UCI initialization.")

    def close(self):
        """Cleanly terminate the underlying Stockfish subprocess."""
        proc = getattr(self, "stockfish_process", None)
        if proc is not None:
            if proc.poll() is None:
                try:
                    self.write_stdin("quit")
                    proc.wait(timeout=1.0)
                except Exception:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.0)
                    except Exception:
                        proc.kill()
            self.stockfish_process = None

    def request_move(self, fen: str) -> str | None:
        """Request the best move from Stockfish for the given FEN position.

        Advances the UCI state machine safely until ``bestmove`` is returned or
        the engine stream closes.

        :param fen: FEN string representing the position to search.
        :type fen: str
        :return: UCI coordinate move string (e.g. ``'e2e4'``), or ``None`` if no move.
        :rtype: str | None
        """
        self.current_state = "WAITING"
        args: dict[str, str | None] = {"inputFEN": fen}
        self.tick(args)
        while self.current_state not in ("WAITING", "DONE"):
            self.tick(args)
        best_move = args.get("bestMove")
        if not best_move or best_move == "(none)":
            return None
        return best_move

    def tick(self, args: dict | None = None):
        """Advance the UCI engine state machine by one step.

        :param args: Dictionary containing ``'inputFEN'`` when requesting a move, and
            populated with ``'bestMove'`` once Stockfish responds.
        :type args: dict | None
        """
        next_state = self.current_state
        match self.current_state:
            case "START_UCI":
                self.write_stdin("uci")
                next_state = "UCI_RESPONSE"
            case "UCI_RESPONSE":
                output = self.read_stdout()
                if output == b"":
                    next_state = "DONE"
                elif output.strip() == b"uciok":
                    next_state = "SET_HASH"
            case "SET_HASH":
                self.write_stdin("setoption name Hash value 32")
                next_state = "INIT_TBS_1"
            case "INIT_TBS_1":
                self.write_stdin("setoption name NalimovCache value 1")
                next_state = "INIT_TBS_2"
            case "INIT_TBS_2":
                self.write_stdin(r"setoption name NalimovPath value d:\tb;c\tb")
                next_state = "SET_UCI_ANALYZE_MODE"
            case "SET_UCI_ANALYZE_MODE":
                self.write_stdin("setoption name UCI_AnalyseMode value false")
                next_state = "SET_DIFFICULTY"
            case "SET_DIFFICULTY":
                self.write_stdin(f"setoption name Skill Level value {self.difficulty}")
                next_state = "IS_READY"
            case "IS_READY":
                self.write_stdin("isready")
                next_state = "READY_OK"
            case "READY_OK":
                output = self.read_stdout()
                if output == b"":
                    next_state = "DONE"
                elif output.strip() == b"readyok":
                    next_state = "NEW_GAME"
            case "NEW_GAME":
                self.write_stdin("ucinewgame")
                next_state = "WAITING"
            case "WAITING":
                next_state = "WAITING"
                if args is not None and "inputFEN" in args:
                    self.inputFEN = args["inputFEN"]
                    next_state = "ASK_CPU"
            case "ASK_CPU":
                movestr = f"position fen {self.inputFEN}"
                self.write_stdin(movestr)
                self.write_stdin(f"go depth {self.depth}")
                next_state = "THINKING"
            case "THINKING":
                output = self.read_stdout()
                if output == b"":
                    if args is not None:
                        args["bestMove"] = None
                    next_state = "DONE"
                else:
                    tokens = output.split()
                    if len(tokens) >= 2 and tokens[0] == b"bestmove":
                        bestMove = tokens[1].decode("utf8", errors="replace")
                        if args is not None:
                            args["bestMove"] = None if bestMove == "(none)" else bestMove
                        next_state = "WAITING"
            case _:
                next_state = "DONE"

        self.current_state = next_state

    def write_stdin(self, message: str):
        """Write a single UCI command line to the Stockfish process stdin.

        :param message: UCI command string (without trailing newline).
        :type message: str
        """
        if self.stockfish_process is not None and self.stockfish_process.stdin is not None:
            self.stockfish_process.stdin.write(f"{message}\n".encode("utf8"))
            self.stockfish_process.stdin.flush()

    def read_stdout(self) -> bytes:
        """Read a single line of output from the Stockfish process stdout.

        :return: Raw bytes line read from stdout (``b''`` on EOF).
        :rtype: bytes
        """
        if self.stockfish_process is None or self.stockfish_process.stdout is None:
            return b""
        return self.stockfish_process.stdout.readline()

    def get_user_move_blocking(self) -> str:
        """Prompt the user on the terminal for a move string.

        :return: Move string entered by the user.
        :rtype: str
        """
        color = "Black" if self.cpu_white else "White"
        return input(f"{color}, what is your move? ")
