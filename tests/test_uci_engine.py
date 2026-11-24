"""Unit tests for uciEngine, engine discovery, and release asset downloader."""

import io
import json
import os
import stat
import subprocess
import tarfile
import urllib.request
import pytest
from pathlib import Path
from uciEngine import (
    EngineSpec,
    KNOWN_ENGINES,
    discover_engines,
    download_engine,
    find_engine_binary,
    select_release_asset,
    uciEngine,
)


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
    assert engine.request_move("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1") is None
    engine.close()


def test_select_release_asset_for_plum_chess_and_stockfish():
    """Verify select_release_asset picks the right binary/archive for each OS and architecture."""
    plum_assets = [
        {
            "name": "plum_chess-v7.16.0-linux-x86_64",
            "browser_download_url": "https://example.com/plum-linux",
        },
        {
            "name": "plum_chess-v7.16.0-macos-aarch64",
            "browser_download_url": "https://example.com/plum-macos",
        },
        {
            "name": "plum_chess-v7.16.0-windows-x86_64.exe",
            "browser_download_url": "https://example.com/plum-win.exe",
        },
    ]
    assert select_release_asset(plum_assets, "linux", "x86_64")["name"] == "plum_chess-v7.16.0-linux-x86_64"
    assert select_release_asset(plum_assets, "macos", "arm64")["name"] == "plum_chess-v7.16.0-macos-aarch64"
    assert select_release_asset(plum_assets, "windows", "x86_64")["name"] == "plum_chess-v7.16.0-windows-x86_64.exe"

    sf_assets = [
        {
            "name": "stockfish-android-arm64-universal.tar.gz",
            "browser_download_url": "https://example.com/sf-android",
        },
        {
            "name": "stockfish-linux-x86-64-universal.tar.gz",
            "browser_download_url": "https://example.com/sf-linux-x64",
        },
        {
            "name": "stockfish-macos-universal.tar.gz",
            "browser_download_url": "https://example.com/sf-macos",
        },
        {
            "name": "stockfish-windows-x86-64-universal.zip",
            "browser_download_url": "https://example.com/sf-win-x64.zip",
        },
    ]
    assert select_release_asset(sf_assets, "linux", "x86_64")["name"] == "stockfish-linux-x86-64-universal.tar.gz"
    assert select_release_asset(sf_assets, "macos", "arm64")["name"] == "stockfish-macos-universal.tar.gz"
    assert select_release_asset(sf_assets, "windows", "x86_64")["name"] == "stockfish-windows-x86-64-universal.zip"


def test_discover_engines_and_download_direct_and_archive(tmp_path, monkeypatch):
    """Verify discover_engines finds binaries in custom directories and download_engine handles raw binaries and tar.gz."""
    # Initially no engines in isolated directory
    plum_bin = tmp_path / "plum_chess"
    plum_bin.write_bytes(b"#!/bin/sh\necho uciok\n")
    plum_bin.chmod(plum_bin.stat().st_mode | stat.S_IXUSR)

    records = discover_engines(extra_dirs=[tmp_path])
    by_key = {r["key"]: r for r in records}
    assert "stockfish" in by_key
    assert "plum_chess" in by_key
    assert by_key["plum_chess"]["installed"] is True
    assert by_key["plum_chess"]["path"] == str(plum_bin.resolve())

    # Test downloading direct binary (Plum_Chess)
    dl_dir = tmp_path / "downloaded"

    def fake_urlopen(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith("/releases/latest") and "Plum_Chess" in url:
            payload = {
                "tag_name": "v7.16.0",
                "assets": [
                    {
                        "name": "plum_chess-v7.16.0-linux-x86_64",
                        "browser_download_url": "https://example.com/plum_bin",
                    }
                ],
            }
            return io.BytesIO(json.dumps(payload).encode("utf-8"))
        if url == "https://example.com/plum_bin":
            return io.BytesIO(b"ELF_PLUM_BINARY")
        if url.endswith("/releases/latest") and "Stockfish" in url:
            payload = {
                "tag_name": "sf_19",
                "assets": [
                    {
                        "name": "stockfish-linux-x86-64-universal.tar.gz",
                        "browser_download_url": "https://example.com/sf.tar.gz",
                    }
                ],
            }
            return io.BytesIO(json.dumps(payload).encode("utf-8"))
        if url == "https://example.com/sf.tar.gz":
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tf:
                data = b"ELF_STOCKFISH_BINARY"
                info = tarfile.TarInfo(name="stockfish/stockfish-ubuntu-x86-64")
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
            buf.seek(0)
            return buf
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    plum_out = Path(download_engine("plum_chess", target_dir=dl_dir, os_name="linux", arch="x86_64"))
    assert plum_out.is_file()
    assert os.access(plum_out, os.X_OK)
    assert plum_out.read_bytes() == b"ELF_PLUM_BINARY"

    sf_out = Path(download_engine("stockfish", target_dir=dl_dir, os_name="linux", arch="x86_64"))
    assert sf_out.is_file()
    assert os.access(sf_out, os.X_OK)
    assert sf_out.read_bytes() == b"ELF_STOCKFISH_BINARY"
