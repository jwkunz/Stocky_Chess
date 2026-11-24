"""UCI engine wrapper, cross-platform engine discovery, and GitHub release downloader."""

import json
import os
import platform
import queue
import shutil
import stat
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EngineSpec:
    """Metadata describing a supported UCI chess engine.

    :ivar key: Short identifier key (e.g. ``'stockfish'``, ``'plum_chess'``).
    :vartype key: str
    :ivar display_name: Human-readable engine name.
    :vartype display_name: str
    :ivar binary_names: Candidate executable names searched on the system.
    :vartype binary_names: tuple[str, ...]
    :ivar github_repo: Optional ``owner/repo`` on GitHub for downloading releases.
    :vartype github_repo: str | None
    """

    key: str
    display_name: str
    binary_names: tuple[str, ...]
    github_repo: str | None = None


KNOWN_ENGINES: tuple[EngineSpec, ...] = (
    EngineSpec(
        key="stockfish",
        display_name="Stockfish",
        binary_names=("stockfish", "stockfish.exe"),
        github_repo="official-stockfish/Stockfish",
    ),
    EngineSpec(
        key="plum_chess",
        display_name="Plum Chess",
        binary_names=("plum_chess", "plum_chess.exe", "Plum_Chess", "Plum_Chess.exe"),
        github_repo="jwkunz/Plum_Chess",
    ),
    EngineSpec(
        key="lc0",
        display_name="Leela Chess Zero (Lc0)",
        binary_names=("lc0", "lc0.exe"),
        github_repo=None,
    ),
    EngineSpec(
        key="komodo",
        display_name="Komodo",
        binary_names=("komodo", "komodo.exe"),
        github_repo=None,
    ),
    EngineSpec(
        key="ethereal",
        display_name="Ethereal",
        binary_names=("ethereal", "ethereal.exe"),
        github_repo=None,
    ),
    EngineSpec(
        key="crafty",
        display_name="Crafty",
        binary_names=("crafty", "crafty.exe"),
        github_repo=None,
    ),
    EngineSpec(
        key="fruit",
        display_name="Fruit",
        binary_names=("fruit", "fruit.exe"),
        github_repo=None,
    ),
    EngineSpec(
        key="glaurung",
        display_name="Glaurung",
        binary_names=("glaurung", "glaurung.exe"),
        github_repo=None,
    ),
    EngineSpec(
        key="toga2",
        display_name="Toga II",
        binary_names=("toga2", "toga2.exe"),
        github_repo=None,
    ),
)


def get_engines_dir() -> Path:
    """Return the local directory where downloaded engines are stored.

    :return: Path to the ``engines/`` directory inside the project.
    :rtype: Path
    """
    return Path("engines")


def _common_search_dirs() -> list[Path]:
    """Return OS-independent common directories where chess engines may be installed."""
    dirs: list[Path] = [
        get_engines_dir(),
        Path.cwd(),
        Path.cwd() / "engines",
        Path.home() / ".local" / "bin",
        Path.home() / "bin",
    ]
    if os.name == "nt":
        for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            val = os.environ.get(env_var)
            if val:
                base = Path(val)
                dirs.extend([base / "Stockfish", base / "Plum_Chess", base / "chess"])
    else:
        dirs.extend(
            [
                Path("/usr/games"),
                Path("/usr/local/games"),
                Path("/usr/local/bin"),
                Path("/usr/bin"),
                Path("/opt/homebrew/bin"),
            ]
        )
    return dirs


def find_engine_binary(spec: EngineSpec, extra_dirs: list[Path] | None = None) -> str | None:
    """Search PATH and common engine directories for a given :class:`EngineSpec`.

    :param spec: Engine specification to search for.
    :type spec: EngineSpec
    :param extra_dirs: Optional additional directories to inspect first.
    :type extra_dirs: list[Path] | None
    :return: Resolved path to the executable if found, otherwise ``None``.
    :rtype: str | None
    """
    search_dirs = (list(extra_dirs) if extra_dirs else []) + _common_search_dirs()

    for d in search_dirs:
        if not d.is_dir():
            continue
        for name in spec.binary_names:
            candidate = d / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate.resolve())
        try:
            for child in sorted(d.iterdir(), reverse=True):
                if child.is_file() and os.access(child, os.X_OK):
                    lower_name = child.name.lower()
                    if lower_name.startswith(spec.key.lower()) and not lower_name.endswith(
                        (".zip", ".tar.gz", ".tgz", ".py")
                    ):
                        return str(child.resolve())
        except OSError:
            pass

    for name in spec.binary_names:
        found = shutil.which(name)
        if found:
            return found

    return None


def discover_engines(extra_dirs: list[Path] | None = None) -> list[dict]:
    """Query the system for known chess engines and report their installation status.

    :param extra_dirs: Optional additional directories to search.
    :type extra_dirs: list[Path] | None
    :return: List of dictionaries with keys ``key``, ``display_name``, ``path``,
        ``installed``, ``downloadable``, and ``github_repo``.
    :rtype: list[dict]
    """
    results: list[dict] = []
    for spec in KNOWN_ENGINES:
        path = find_engine_binary(spec, extra_dirs=extra_dirs)
        results.append(
            {
                "key": spec.key,
                "display_name": spec.display_name,
                "path": path,
                "installed": path is not None,
                "downloadable": spec.github_repo is not None,
                "github_repo": spec.github_repo,
            }
        )
    return results


def detect_system_platform() -> tuple[str, str]:
    """Return normalized ``(os_name, arch)`` for the current host.

    ``os_name`` is one of ``'linux'``, ``'windows'``, or ``'macos'``.
    ``arch`` is one of ``'x86_64'``, ``'arm64'``, or the lowercased machine string.

    :return: Tuple ``(os_name, arch)``.
    :rtype: tuple[str, str]
    """
    sys_raw = platform.system().lower()
    if sys_raw.startswith("win") or os.name == "nt":
        os_name = "windows"
    elif sys_raw == "darwin":
        os_name = "macos"
    else:
        os_name = "linux"

    machine_raw = platform.machine().lower()
    if machine_raw in ("x86_64", "amd64"):
        arch = "x86_64"
    elif machine_raw in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        arch = machine_raw

    return (os_name, arch)


def select_release_asset(
    assets: list[dict],
    os_name: str | None = None,
    arch: str | None = None,
) -> dict | None:
    """Select the best matching GitHub release asset for the target OS and CPU architecture.

    :param assets: List of GitHub release asset dicts containing ``'name'`` and ``'browser_download_url'``.
    :type assets: list[dict]
    :param os_name: Normalized OS name (``'linux'``, ``'windows'``, ``'macos'``).
    :type os_name: str | None
    :param arch: Normalized CPU architecture (``'x86_64'``, ``'arm64'``).
    :type arch: str | None
    :return: Matching asset dictionary, or ``None`` if no compatible asset is found.
    :rtype: dict | None
    """
    if os_name is None or arch is None:
        det_os, det_arch = detect_system_platform()
        os_name = os_name or det_os
        arch = arch or det_arch

    os_tokens = {
        "linux": ("linux",),
        "windows": ("windows", "win"),
        "macos": ("macos", "darwin", "osx", "mac"),
    }.get(os_name, (os_name,))

    arch_tokens = {
        "x86_64": ("x86_64", "x86-64", "amd64", "x64"),
        "arm64": ("arm64", "aarch64"),
    }.get(arch, (arch,))

    scored: list[tuple[int, dict]] = []
    for asset in assets:
        name = asset.get("name", "").lower()
        if "android" in name or name.endswith((".sha256", ".sig", ".txt")):
            continue
        if not any(tok in name for tok in os_tokens):
            continue

        score = 10
        if any(tok in name for tok in arch_tokens):
            score += 20
        elif "universal" in name:
            score += 10
        else:
            continue

        if "universal" in name:
            score += 5
        if "avx512" in name or "vnni" in name:
            score -= 5
        scored.append((score, asset))

    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def download_engine(
    engine_key: str,
    target_dir: Path | None = None,
    os_name: str | None = None,
    arch: str | None = None,
) -> str:
    """Download and extract the latest release of ``engine_key`` for the current architecture.

    Supports both direct binary assets (such as ``Plum_Chess``) and compressed archives
    (``.tar.gz`` / ``.zip`` such as ``Stockfish``).

    :param engine_key: Engine identifier (e.g. ``'stockfish'`` or ``'plum_chess'``).
    :type engine_key: str
    :param target_dir: Destination directory for the executable (defaults to :func:`get_engines_dir`).
    :type target_dir: Path | None
    :param os_name: Optional OS override for testing.
    :type os_name: str | None
    :param arch: Optional architecture override for testing.
    :type arch: str | None
    :return: Absolute path to the downloaded and executable engine binary.
    :rtype: str
    :raises ValueError: If the engine key is unknown or has no GitHub repository.
    :raises RuntimeError: If no matching release asset is found or download fails.
    """
    spec = next((s for s in KNOWN_ENGINES if s.key == engine_key), None)
    if spec is None or not spec.github_repo:
        raise ValueError(f"Engine '{engine_key}' does not support automatic download.")

    if os_name is None or arch is None:
        det_os, det_arch = detect_system_platform()
        os_name = os_name or det_os
        arch = arch or det_arch

    dest_dir = Path(target_dir) if target_dir is not None else get_engines_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    api_url = f"https://api.github.com/repos/{spec.github_repo}/releases/latest"
    req = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Stocky-Chess-Updater",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            release_data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to query GitHub releases for {spec.display_name}: {exc}") from exc

    assets = release_data.get("assets", [])
    asset = select_release_asset(assets, os_name=os_name, arch=arch)
    if asset is None:
        raise RuntimeError(
            f"No compatible release asset found for {spec.display_name} on {os_name}/{arch}."
        )

    download_url = asset["browser_download_url"]
    asset_name = asset["name"]
    binary_filename = f"{spec.key}.exe" if os_name == "windows" else spec.key
    final_binary_path = dest_dir / binary_filename

    dl_req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "Stocky-Chess-Updater"},
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / asset_name
        try:
            with urllib.request.urlopen(dl_req, timeout=120) as resp, open(tmp_path, "wb") as out_file:
                shutil.copyfileobj(resp, out_file)
        except Exception as exc:
            raise RuntimeError(f"Failed to download {download_url}: {exc}") from exc

        extract_dir = Path(tmpdir) / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        lower_asset = asset_name.lower()
        if lower_asset.endswith((".tar.gz", ".tgz")):
            with tarfile.open(tmp_path, "r:gz") as tar:
                tar.extractall(path=extract_dir, filter="data")
            extracted_bin = _find_extracted_binary(extract_dir, spec)
            shutil.copy2(extracted_bin, final_binary_path)
        elif lower_asset.endswith(".zip"):
            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(path=extract_dir)
            extracted_bin = _find_extracted_binary(extract_dir, spec)
            shutil.copy2(extracted_bin, final_binary_path)
        else:
            shutil.copy2(tmp_path, final_binary_path)

    current_mode = final_binary_path.stat().st_mode
    final_binary_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(final_binary_path.resolve())


def _find_extracted_binary(extract_dir: Path, spec: EngineSpec) -> Path:
    """Locate the main engine executable inside an extracted archive directory."""
    candidates: list[Path] = []
    for root, _, files in os.walk(extract_dir):
        for fname in files:
            fpath = Path(root) / fname
            lower = fname.lower()
            if lower.endswith((".txt", ".md", ".pdf", ".1", ".cpp", ".h", ".o", ".nnue")):
                continue
            if fname in spec.binary_names or lower.startswith(spec.key.lower()):
                candidates.append(fpath)
    if not candidates:
        raise RuntimeError(f"Could not find executable for {spec.display_name} in downloaded archive.")
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def resolve_stockfish_path(path: str | None = None) -> str:
    """Resolve the path to a UCI engine executable across platforms.

    :param path: Explicit path or binary name, or ``None`` to auto-detect.
    :type path: str | None
    :return: Resolved executable path or fallback binary name.
    :rtype: str
    """
    if path:
        resolved = shutil.which(path) or (path if os.path.isfile(path) else None)
        if resolved:
            return resolved
        by_key = next((s for s in KNOWN_ENGINES if s.key == path), None)
        if by_key is not None:
            found = find_engine_binary(by_key)
            if found:
                return found

    for spec in KNOWN_ENGINES:
        found = find_engine_binary(spec)
        if found:
            return found

    return path if path else ("stockfish.exe" if os.name == "nt" else "stockfish")


def parse_uci_option_line(line: str) -> tuple[str, dict] | None:
    """Parse a UCI ``option name ... type ...`` line into ``(option_name, metadata)``.

    :param line: Decoded text line emitted by an engine during the ``uci`` handshake.
    :type line: str
    :return: Tuple ``(name, info_dict)`` or ``None`` if not an option line.
    :rtype: tuple[str, dict] | None
    """
    stripped = line.strip()
    if not stripped.startswith("option name "):
        return None
    tokens = stripped.split()
    if "type" not in tokens:
        return None
    type_idx = tokens.index("type")
    opt_name = " ".join(tokens[2:type_idx])
    opt_type = tokens[type_idx + 1] if type_idx + 1 < len(tokens) else "string"
    info: dict[str, str | int | None] = {"type": opt_type, "min": None, "max": None}
    for i in range(type_idx + 2, len(tokens) - 1):
        if tokens[i] == "min":
            try:
                info["min"] = int(tokens[i + 1])
            except ValueError:
                pass
        elif tokens[i] == "max":
            try:
                info["max"] = int(tokens[i + 1])
            except ValueError:
                pass
    return (opt_name, info)


class uciEngine:
    """Manages a UCI chess engine subprocess with a non-blocking search harness.

    Parses advertised UCI options during handshake so only supported options are sent
    with properly clamped values (e.g. ``Skill Level`` max 10 for Plum Chess vs 20 for Stockfish),
    and supports both synchronous :meth:`request_move` and asynchronous
    :meth:`start_search` / :meth:`poll_move` for non-blocking GUI play.

    :ivar stockfish_process: The underlying engine Popen process.
    :vartype stockfish_process: subprocess.Popen | None
    :ivar current_state: Current state in the UCI handshake/search state machine.
    :vartype current_state: str
    :ivar difficulty: Configured engine Skill Level.
    :vartype difficulty: int
    :ivar depth: Search depth passed to ``go``.
    :vartype depth: int
    :ivar movetime_ms: Per-move time cap in milliseconds passed to ``go``.
    :vartype movetime_ms: int
    :ivar engine_path: Resolved path to the engine binary.
    :vartype engine_path: str
    :ivar engine_name: Engine name reported via ``id name`` or derived from binary.
    :vartype engine_name: str
    :ivar supported_options: Advertised UCI options parsed during initialization.
    :vartype supported_options: dict[str, dict]
    """

    def __init__(
        self,
        path: str | None = None,
        difficulty: int = 10,
        moveDepth: int = 10,
        movetime_ms: int = 1500,
    ):
        """Launch a UCI engine and run the UCI initialization state machine until ready.

        :param path: Path or key for the UCI engine executable.
        :type path: str | None
        :param difficulty: Requested Skill Level (automatically clamped to engine's min/max).
        :type difficulty: int
        :param moveDepth: Search depth in plies.
        :type moveDepth: int
        :param movetime_ms: Maximum search time per move in milliseconds.
        :type movetime_ms: int
        """
        self.engine_path = resolve_stockfish_path(path)
        self.engine_name = Path(self.engine_path).stem.replace("_", " ").title()
        self.supported_options: dict[str, dict] = {}
        self.stockfish_process = subprocess.Popen(
            [self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.current_state = "START_UCI"
        self.difficulty = max(0, min(20, int(difficulty)))
        self.depth = max(1, int(moveDepth))
        self.movetime_ms = max(100, int(movetime_ms))
        self.inputFEN = ""
        self.cpu_white = False
        self._async_thread: threading.Thread | None = None
        self._async_queue: queue.Queue[str | None] = queue.Queue()
        self._lock = threading.Lock()

        while self.current_state not in ("WAITING", "DONE"):
            self.tick()
        if self.current_state == "DONE":
            self.close()
            raise RuntimeError("UCI engine process exited unexpectedly during initialization.")

    def _clamp_option(self, name: str, value: int) -> int:
        """Clamp an integer spin option value to the engine's advertised ``[min, max]`` range."""
        opt = self.supported_options.get(name)
        if not opt:
            return value
        lo = opt.get("min")
        hi = opt.get("max")
        if lo is not None:
            value = max(int(lo), value)
        if hi is not None:
            value = min(int(hi), value)
        return value

    def close(self):
        """Cleanly terminate the underlying UCI engine subprocess."""
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
        """Synchronously request the best move from the UCI engine for ``fen``.

        :param fen: FEN string representing the position to search.
        :type fen: str
        :return: UCI coordinate move string (e.g. ``'e2e4'``), or ``None`` if no move.
        :rtype: str | None
        """
        with self._lock:
            if self.stockfish_process is None or self.stockfish_process.poll() is not None:
                return None
            self.current_state = "WAITING"
            args: dict[str, str | None] = {"inputFEN": fen}
            self.tick(args)
            while self.current_state not in ("WAITING", "DONE"):
                self.tick(args)
            best_move = args.get("bestMove")
            if not best_move or best_move == "(none)":
                return None
            return best_move

    def start_search(self, fen: str):
        """Start an asynchronous move search in a background worker thread.

        Use :meth:`poll_move` to check whether the search has completed without
        blocking the GUI event loop.

        :param fen: FEN string representing the position to search.
        :type fen: str
        """
        if self.is_searching():
            return
        while not self._async_queue.empty():
            try:
                self._async_queue.get_nowait()
            except queue.Empty:
                break

        def _worker():
            move = self.request_move(fen)
            self._async_queue.put(move)

        self._async_thread = threading.Thread(target=_worker, daemon=True)
        self._async_thread.start()

    def is_searching(self) -> bool:
        """Return ``True`` if a background search thread is currently active."""
        return self._async_thread is not None and self._async_thread.is_alive()

    def poll_move(self) -> tuple[bool, str | None]:
        """Check whether an asynchronous search started with :meth:`start_search` has finished.

        :return: Tuple ``(done, move)`` where ``done`` is ``True`` once the search completes.
        :rtype: tuple[bool, str | None]
        """
        try:
            move = self._async_queue.get_nowait()
            self._async_thread = None
            return (True, move)
        except queue.Empty:
            if self._async_thread is not None and not self._async_thread.is_alive():
                self._async_thread = None
                return (True, None)
            return (False, None)

    def tick(self, args: dict | None = None):
        """Advance the UCI engine state machine by one step.

        :param args: Dictionary containing ``'inputFEN'`` when requesting a move, and
            populated with ``'bestMove'`` once the engine responds.
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
                else:
                    text_line = output.decode("utf8", errors="replace").strip()
                    if text_line.startswith("id name "):
                        self.engine_name = text_line[len("id name ") :].strip()
                    else:
                        parsed = parse_uci_option_line(text_line)
                        if parsed is not None:
                            opt_name, opt_info = parsed
                            self.supported_options[opt_name] = opt_info
                    if text_line == "uciok":
                        next_state = "SET_HASH"
            case "SET_HASH":
                if not self.supported_options or "Hash" in self.supported_options:
                    hash_val = self._clamp_option("Hash", 32)
                    self.write_stdin(f"setoption name Hash value {hash_val}")
                next_state = "SET_DIFFICULTY"
            case "SET_DIFFICULTY":
                if not self.supported_options or "Skill Level" in self.supported_options:
                    skill_val = self._clamp_option("Skill Level", self.difficulty)
                    self.difficulty = skill_val
                    self.write_stdin(f"setoption name Skill Level value {skill_val}")
                if "Threads" in self.supported_options:
                    self.write_stdin("setoption name Threads value 1")
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
                self.write_stdin(f"go depth {self.depth} movetime {self.movetime_ms}")
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
        """Write a single UCI command line to the engine process stdin.

        :param message: UCI command string (without trailing newline).
        :type message: str
        """
        if self.stockfish_process is not None and self.stockfish_process.stdin is not None:
            self.stockfish_process.stdin.write(f"{message}\n".encode("utf8"))
            self.stockfish_process.stdin.flush()

    def read_stdout(self) -> bytes:
        """Read a single line of output from the engine process stdout.

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
