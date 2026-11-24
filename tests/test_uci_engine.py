"""Unit tests for uciEngine using a mock subprocess pipe."""

import io
import subprocess
import pytest
from uciEngine import uciEngine, resolve_stockfish_path


class FakeProcess:
    """In-memory mock of subprocess.Popen for testing UCI protocol interactions."""

    def __init__(self, stdout_lines: list[bytes]):
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO(b"".join(stdout_lines))
        self.terminated = False

    def poll(self):
        return 0 if self.terminated else None

    def wait(self, timeout=None):
        self.terminated = True
        return 0

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.terminated = True


def test_uci_engine_handshake_and_request_move(monkeypatch):
    """Verify uciEngine completes handshake with LF/CRLF and parses bestmove skipping blank/info lines."""
    fake_proc = FakeProcess(
        [
            b"Stockfish 16 by the Stockfish developers\n",
            b"\n",
            b"uciok\n",
            b"readyok\r\n",
            b"info depth 1 score cp 20 pv e2e4\n",
            b"\n",
            b"bestmove e2e4 ponder e7e5\n",
        ]
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: fake_proc)

    engine = uciEngine(path="stockfish", difficulty=12, moveDepth=15)
    assert engine.current_state == "WAITING"
    assert engine.difficulty == 12
    assert engine.depth == 15

    move = engine.request_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert move == "e2e4"
    assert engine.current_state == "WAITING"

    written = fake_proc.stdin.getvalue().decode("utf8")
    assert "uci\n" in written
    assert "setoption name Skill Level value 12\n" in written
    assert "go depth 15\n" in written

    engine.close()
    assert engine.stockfish_process is None


def test_uci_engine_handles_bestmove_none_and_eof(monkeypatch):
    """Verify uciEngine returns None instead of crashing on bestmove (none) or EOF."""
    fake_proc = FakeProcess(
        [
            b"uciok\n",
            b"readyok\n",
            b"bestmove (none)\n",
        ]
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: fake_proc)

    engine = uciEngine(path="stockfish", difficulty=5, moveDepth=5)
    assert engine.request_move("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1") is None
    # Second call hits EOF on stdout
    assert engine.request_move("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1") is None
    engine.close()
