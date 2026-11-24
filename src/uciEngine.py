"""UCI engine wrapper for communicating with a Stockfish subprocess."""

from random import randint
import time
import subprocess


class uciEngine():
    """Manages a Stockfish engine subprocess via the Universal Chess Interface (UCI) protocol.

    :ivar stockfish_process: The underlying Stockfish Popen process.
    :vartype stockfish_process: subprocess.Popen
    :ivar current_state: Current state in the UCI handshake/search state machine.
    :vartype current_state: str
    :ivar difficulty: Configured Stockfish Skill Level (1-20).
    :vartype difficulty: int
    :ivar depth: Search depth passed to ``go depth``.
    :vartype depth: int
    """

    def __init__(self,path='stockfish.exe',difficulty=20,moveDepth=20):
        """Launch Stockfish and run the UCI initialization state machine until ready.

        :param path: Path to the Stockfish executable.
        :type path: str
        :param difficulty: Stockfish Skill Level (1 to 20).
        :type difficulty: int
        :param moveDepth: Search depth in plies.
        :type moveDepth: int
        """
        # Launch the executable in a subprocess
        self.stockfish_process = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        # Initial state
        self.current_state = "START_UCI"
        # Difficulty 
        self.difficulty = difficulty
        # Depth
        self.depth = moveDepth
        # Initialize
        while(self.current_state != "WAITING"):
            self.tick()

    def tick(self,args=None):
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
                if(output == b"uciok\r\n"):
                    next_state = "SET_HASH"
            case "SET_HASH":
                self.write_stdin("setoption name Hash value 32")
                next_state = "INIT_TBS_1"
            case "INIT_TBS_1":
                self.write_stdin("setoption name NalimovCache value 1")
                next_state = "INIT_TBS_2"
            case "INIT_TBS_2":
                self.write_stdin("setoption name NalimovPath value d:\tb;c\tb")
                next_state = "SET_UCI_ANALYZE_MODE"
            case "SET_UCI_ANALYZE_MODE":
                self.write_stdin("setoption name UCI_AnalyseMode value true")
                next_state = "SET_DIFFICULTY"
            case "SET_DIFFICULTY":
                self.write_stdin(f"setoption name Skill Level value {self.difficulty}")
                next_state = "IS_READY"                
            case "IS_READY":
                self.write_stdin("isready")
                next_state = "READY_OK"
            case "READY_OK":
                output = self.read_stdout()
                if(output == b"readyok\r\n"):
                    next_state = "NEW_GAME"
            case "NEW_GAME":
                self.write_stdin("ucinewgame")
                next_state = "WAITING"
            case "WAITING":
                next_state = "WAITING"       
                if(args != None and ("inputFEN" in args.keys())):
                    self.inputFEN = args["inputFEN"]
                    next_state = "ASK_CPU"
            case "ASK_CPU":
                movestr = f"position fen {self.inputFEN}"
                self.write_stdin(movestr)
                self.write_stdin(f"go depth {self.depth}")
                next_state = "THINKING"
            case "THINKING":
                output = self.read_stdout()
                tokens = output.split()
                if(tokens[0] == b'bestmove'):
                    bestMove = tokens[1].decode('utf8')
                    args["bestMove"] = bestMove
                    next_state = "WAITING"
            case _:
                next_state = "DONE"

        self.current_state = next_state

    def write_stdin(self,message):
        """Write a single UCI command line to the Stockfish process stdin.

        :param message: UCI command string (without trailing newline).
        :type message: str
        """
        self.stockfish_process.stdin.write(bytes(f'{message}\n',"utf8"))
        self.stockfish_process.stdin.flush()  

    def read_stdout(self):
        """Read a single line of output from the Stockfish process stdout.

        :return: Raw bytes line read from stdout.
        :rtype: bytes
        """
        line = self.stockfish_process.stdout.readline()
        return line
    
    def get_user_move_blocking(self):
        """Prompt the user on the terminal for a move string.

        :return: Move string entered by the user.
        :rtype: str
        """
        color = "White"
        if(self.cpu_white):
            color = "Black"
        move = input(f"{color}, what is your move? ")
        
        # Check if valid
        # Skip

        # Return
        return move
