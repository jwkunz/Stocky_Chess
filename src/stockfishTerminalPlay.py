"""Standalone terminal interface for playing chess against Stockfish over UCI."""

from random import randint
import time
import subprocess

### Use this one to play with in stand alone mode


class stockfishTerminalPlay():
    """Interactive command-line chess session against a Stockfish subprocess.

    :cvar debug_mode: When ``True``, prints UCI traffic to stdout.
    :vartype debug_mode: bool
    """

    debug_mode = False

    def __init__(self):
        """Launch the Stockfish executable and set the initial UCI state."""
        self.debug_print("Initializing Game by Launching Engine...")
        # Launch the executable in a subprocess
        self.stockfish_process = subprocess.Popen(['stockfish.exe'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        # Initial state
        self.current_state = "START_UCI"
        self.debug_print("Launched Engine...")

    def tick(self):
        """Advance the terminal game state machine by one step."""
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
                difficulty = int(input("What difficulty is the CPU (0-20)?"))
                self.write_stdin(f"setoption name Skill Level value {difficulty}")
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
                self.move_history = ""
                next_state = "STARTING_MOVES"
            case "STARTING_MOVES":
                response = input("User Plays White (w) or Black (b) or Random (r)?")
                if(response.upper() == "R"):
                    self.cpu_white = (randint(0,1) % 2 == 0)
                else:
                    self.cpu_white = (response.upper() == "B")

                if(self.cpu_white):
                    print("CPU IS WHITE. USER IS BLACK")
                    next_state = "ASK_CPU"
                else:
                    print("CPU IS BLACK. USER IS WHITE")
                    next_state = "GET_USER"
            case "GET_USER":
                # Get User's move
                self.move_history += f" {self.get_user_move_blocking()}"               
                next_state = "ASK_CPU"
            case "ASK_CPU":
                movestr = f"position startpos moves{self.move_history}"
                self.write_stdin(movestr)
                self.write_stdin("go movetime 2000")
                next_state = "THINKING"
                print("CPU IS THINKING...")
            case "THINKING":
                output = self.read_stdout()
                tokens = output.split()
                if(tokens[0] == b'bestmove'):
                    move = tokens[1].decode('utf8')
                    self.move_history += f" {move}"
                    print(f"CPU MOVES: {move}")
                    next_state = "GET_USER"                


            case "EXIT":
                self.debug_print("Terminating")
                self.write_stdin("quit")
                next_state = "EXIT"
                exit()
            case _:
                next_state = "EXIT"

        self.current_state = next_state

    def write_stdin(self,message):
        """Send a UCI command line to Stockfish.

        :param message: UCI command string.
        :type message: str
        """
        self.stockfish_process.stdin.write(bytes(f'{message}\n',"utf8"))
        self.stockfish_process.stdin.flush()  
        self.debug_print(f"WROTE:{message}")

    def read_stdout(self):
        """Read a single line from Stockfish stdout.

        :return: Raw bytes line from Stockfish.
        :rtype: bytes
        """
        line = self.stockfish_process.stdout.readline()
        self.debug_print(f"READ:{line}")
        return line
    
    def get_user_move_blocking(self):
        """Prompt the user for a move via standard input.

        :return: The user's move in UCI algebraic notation.
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

    def debug_print(self,message):
        """Print a debug message if :attr:`debug_mode` is enabled.

        :param message: Message string to print.
        :type message: str
        """
        if(self.debug_mode):
            print(f"DEBUG->{message}\n")


# Debug Tester
if __name__ == "__main__":
    print("Starting UCI manager")
    S = stockfishTerminalPlay()
    S.debug_mode = True
    while(True):
        #time.sleep(0.1)
        S.tick()
