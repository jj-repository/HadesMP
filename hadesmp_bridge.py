#!/usr/bin/env python3
"""
HadesMP Bridge — Python-side IPC for the HadesMP multiplayer mod.

Communicates with the Lua bridge running inside Hades (via Wine/Proton):
  - Lua→Python: tails hades_lua_stdout.log for HADESMP: prefixed lines
  - Python→Lua: writes hadesmp_inbox.lua atomically for Lua to dofile()

Usage:
    python3 hadesmp_bridge.py [--game-dir /path/to/Hades/x64Vk]
"""

import argparse
import os
import re
import sys
import tempfile
import threading
import time
from pathlib import Path

# Default game directory (x64Vk is the CWD when Hades runs)
DEFAULT_GAME_DIR = Path("/mnt/ext4gamedrive/SteamLibrary/steamapps/common/Hades/x64Vk")

STDOUT_LOG = "hades_lua_stdout.log"
INBOX_FILE = "hadesmp_inbox.lua"
HADESMP_PREFIX = "HADESMP:"


class StdoutWatcher:
    """Daemon thread that tail-follows the stdout log for HADESMP: messages."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.callbacks: list = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="stdout-watcher")
        self._last_size = -1  # sentinel: -1 = never started, 0+ = file position

    def add_callback(self, fn):
        """Register a callback: fn(msg_type: str, payload: str)"""
        self.callbacks.append(fn)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        """Tail-follow the log file, handling truncation (game restart)."""
        while not self._stop_event.is_set():
            try:
                if not self.log_path.exists():
                    self._stop_event.wait(0.5)
                    continue

                with open(self.log_path, "r", errors="replace") as f:
                    # Seek to where we left off
                    f.seek(0, 2)  # end of file
                    current_size = f.tell()

                    if self._last_size < 0:
                        # First run — start from current end (don't replay old logs)
                        self._last_size = current_size
                        self._stop_event.wait(0.1)
                        continue
                    elif current_size < self._last_size:
                        # File was truncated (game restarted) — read from start
                        f.seek(0)
                    else:
                        f.seek(self._last_size)

                    while not self._stop_event.is_set():
                        line = f.readline()
                        if not line:
                            self._last_size = f.tell()
                            self._stop_event.wait(0.05)
                            # Clear Python's EOF cache so we see new data
                            f.seek(self._last_size)
                            # Check for truncation
                            try:
                                new_size = self.log_path.stat().st_size
                                if new_size < self._last_size:
                                    break  # re-open
                            except OSError:
                                break
                            continue

                        line = line.rstrip("\n\r")
                        if line.startswith(HADESMP_PREFIX):
                            rest = line[len(HADESMP_PREFIX):]
                            colon = rest.find(":")
                            if colon >= 0:
                                msg_type = rest[:colon]
                                payload = rest[colon + 1:]
                            else:
                                msg_type = rest
                                payload = ""
                            self._dispatch(msg_type, payload)

            except Exception as e:
                print(f"[watcher] error: {e}", file=sys.stderr)
                self._stop_event.wait(1.0)

    def _dispatch(self, msg_type: str, payload: str):
        for cb in self.callbacks:
            try:
                cb(msg_type, payload)
            except Exception as e:
                print(f"[watcher] callback error: {e}", file=sys.stderr)


class InboxWriter:
    """Writes messages to hadesmp_inbox.lua atomically."""

    def __init__(self, inbox_path: Path):
        self.inbox_path = inbox_path
        self._seq = self._read_existing_seq(inbox_path)
        self._lock = threading.Lock()

    @staticmethod
    def _read_existing_seq(path: Path) -> int:
        """Read seq from existing inbox file to avoid seq rollback."""
        try:
            import re
            text = path.read_text()
            m = re.search(r"seq\s*=\s*(\d+)", text)
            if m:
                return int(m.group(1))
        except (OSError, ValueError):
            pass
        return 0

    @property
    def seq(self):
        return self._seq

    def write(self, messages: list[str]):
        """Write a batch of messages to the inbox file atomically.

        Each message is a string like "PING:1709312345.123" or "EXEC:print('hi')".
        """
        with self._lock:
            self._seq += 1
            seq = self._seq

            # Encode messages as Lua long-strings with proper escaping
            lua_msgs = []
            for msg in messages:
                # Find the right number of = signs for long string delimiters
                eq_count = 0
                while f"]{'=' * eq_count}]" in msg:
                    eq_count += 1
                eq = "=" * eq_count
                lua_msgs.append(f"[{eq}[{msg}]{eq}]")

            msgs_lua = ",\n    ".join(lua_msgs)
            content = f"return {{\n  seq = {seq},\n  msgs = {{\n    {msgs_lua}\n  }}\n}}\n"

            # Write to temp file then atomically replace
            dir_path = self.inbox_path.parent
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".hadesmp_inbox_", suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                # Ensure world-readable (needed when running as root/sudo)
                os.chmod(tmp_path, 0o644)
                os.replace(tmp_path, self.inbox_path)
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

        return seq

    def write_single(self, msg: str) -> int:
        """Convenience: write a single message."""
        return self.write([msg])


class HadesMPBridge:
    """Main bridge: ties StdoutWatcher + InboxWriter together."""

    def __init__(self, game_dir: Path):
        self.game_dir = game_dir
        self.watcher = StdoutWatcher(game_dir / STDOUT_LOG)
        self.writer = InboxWriter(game_dir / INBOX_FILE)

        # State tracking
        self.lua_version: str | None = None
        self.lua_ready = threading.Event()
        self.last_heartbeat: float = 0
        self.heartbeat_count = 0
        self.pending_pings: dict[str, float] = {}  # timestamp_str -> send_time
        self.last_rtt: float | None = None
        self.acked_seqs: set[int] = set()
        self._lock = threading.Lock()

        # P2 state
        self.p2_spawned = False
        self.p2_object_id: int | None = None
        self.p1_position: tuple[float, float, float] | None = None  # (x, y, angle)
        self.current_room: str | None = None
        self.p2_events: list[tuple[float, str]] = []  # (time, event_payload)
        self._p2_event = threading.Event()  # signals when a P2EVT arrives
        self._p1pos_count = 0

        # Message log for debugging
        self.message_log: list[tuple[float, str, str]] = []  # (time, type, payload)
        self._max_log = 100

        # Register handlers
        self.watcher.add_callback(self._on_message)

    def start(self):
        """Start the watcher thread."""
        log_path = self.game_dir / STDOUT_LOG
        if not log_path.exists():
            print(f"[bridge] warning: {log_path} not found — waiting for game to start")
        self.watcher.start()
        print(f"[bridge] watching {log_path}")
        print(f"[bridge] inbox at {self.game_dir / INBOX_FILE}")

    def stop(self):
        self.watcher.stop()

    def _on_message(self, msg_type: str, payload: str):
        """Handle incoming messages from Lua."""
        now = time.time()

        with self._lock:
            self.message_log.append((now, msg_type, payload))
            if len(self.message_log) > self._max_log:
                self.message_log = self.message_log[-self._max_log:]

        if msg_type == "INIT":
            self.lua_version = payload
            print(f"[bridge] Lua INIT: {payload}")

        elif msg_type == "READY":
            self.lua_ready.set()
            print(f"[bridge] Lua READY")

        elif msg_type == "HB":
            self.last_heartbeat = now
            self.heartbeat_count += 1

        elif msg_type == "ACK":
            try:
                seq = int(payload)
                self.acked_seqs.add(seq)
            except ValueError:
                pass

        elif msg_type == "PONG":
            ts_str = payload
            with self._lock:
                if ts_str in self.pending_pings:
                    send_time = self.pending_pings.pop(ts_str)
                    self.last_rtt = (now - send_time) * 1000  # ms
                    print(f"[bridge] PONG: RTT = {self.last_rtt:.1f} ms")

        elif msg_type == "EXEC_OK":
            print(f"[bridge] EXEC OK: {payload}")

        elif msg_type == "EXEC_ERR":
            print(f"[bridge] EXEC ERROR: {payload}")

        elif msg_type == "MSG":
            print(f"[bridge] MSG: {payload}")

        elif msg_type == "P2EVT":
            now_ts = time.time()
            with self._lock:
                self.p2_events.append((now_ts, payload))
                if len(self.p2_events) > 50:
                    self.p2_events = self.p2_events[-50:]
            if payload.startswith("spawned="):
                self.p2_spawned = True
                try:
                    self.p2_object_id = int(payload.split("=", 1)[1])
                except ValueError:
                    pass
            elif payload.startswith("despawned"):
                self.p2_spawned = False
                self.p2_object_id = None
            elif payload == "enabled":
                pass  # P2 mode enabled, spawn will follow
            elif payload == "disabled":
                self.p2_spawned = False
                self.p2_object_id = None
            print(f"[bridge] P2EVT: {payload}")
            self._p2_event.set()

        elif msg_type == "P1POS":
            parts = payload.split(",")
            if len(parts) >= 3:
                try:
                    self.p1_position = (float(parts[0]), float(parts[1]), float(parts[2]))
                    self._p1pos_count += 1
                except ValueError:
                    pass

        elif msg_type == "ROOM":
            self.current_room = payload
            print(f"[bridge] ROOM: {payload}")

        elif msg_type == "HOOK_ERR":
            print(f"[bridge] HOOK ERROR: {payload}")

        elif msg_type == "PROXY":
            # From VERSION.dll proxy — stdout redirect confirmation
            print(f"[bridge] proxy: {payload}")

        else:
            print(f"[bridge] unknown: {msg_type}:{payload}")

    def ping(self) -> int:
        """Send a PING and track it for RTT measurement."""
        ts = f"{time.time():.6f}"
        with self._lock:
            self.pending_pings[ts] = time.time()
        return self.writer.write_single(f"PING:{ts}")

    def send_msg(self, text: str) -> int:
        """Send a generic MSG to Lua."""
        return self.writer.write_single(f"MSG:{text}")

    def exec_lua(self, code: str) -> int:
        """Execute arbitrary Lua code in the game."""
        return self.writer.write_single(f"EXEC:{code}")

    def send_nop(self) -> int:
        """Send a NOP (no-op) to test the channel without side effects."""
        return self.writer.write_single("NOP")

    # ---- P2 Controller API ----

    def p2_enable(self) -> int:
        """Enable P2 spawning."""
        return self.writer.write_single("P2ENABLE:1")

    def p2_disable(self) -> int:
        """Disable P2 and despawn."""
        return self.writer.write_single("P2ENABLE:0")

    def p2_teleport(self, x: float, y: float) -> int:
        """Teleport P2 to absolute position."""
        return self.writer.write_single(f"P2POS:{x},{y}")

    def p2_move(self, dx: float, dy: float) -> int:
        """Move P2 by relative delta."""
        return self.writer.write_single(f"P2MOVE:{dx},{dy}")

    def p2_face(self, angle: float) -> int:
        """Set P2 facing angle."""
        return self.writer.write_single(f"P2FACE:{angle}")

    def p2_fire(self, weapon: str = "SwordWeapon") -> int:
        """Fire weapon from P2."""
        return self.writer.write_single(f"P2FIRE:{weapon}")

    def p2_anim(self, name: str) -> int:
        """Set P2 animation."""
        return self.writer.write_single(f"P2ANIM:{name}")

    def p2_sync(self, x: float, y: float, angle: float, anim: str = "") -> int:
        """Combined position+facing+animation update (one msg per tick)."""
        return self.writer.write_single(f"P2SYNC:{x},{y},{angle},{anim}")

    def wait_p2_event(self, prefix: str = "", timeout: float = 5.0) -> str | None:
        """Wait for a P2EVT matching the given prefix. Returns payload or None on timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._p2_event.clear()
            with self._lock:
                for ts, payload in self.p2_events:
                    if payload.startswith(prefix):
                        return payload
            self._p2_event.wait(timeout=min(0.1, deadline - time.time()))
        return None

    def clear_p2_events(self):
        """Clear accumulated P2 events."""
        with self._lock:
            self.p2_events.clear()
        self._p2_event.clear()

    def status(self) -> dict:
        """Return current bridge status."""
        now = time.time()
        hb_ago = now - self.last_heartbeat if self.last_heartbeat else None
        return {
            "lua_version": self.lua_version,
            "lua_ready": self.lua_ready.is_set(),
            "heartbeats": self.heartbeat_count,
            "last_heartbeat_ago": f"{hb_ago:.1f}s" if hb_ago is not None else "never",
            "last_rtt_ms": f"{self.last_rtt:.1f}" if self.last_rtt is not None else "n/a",
            "inbox_seq": self.writer.seq,
            "acked_seqs": len(self.acked_seqs),
            "p2_spawned": self.p2_spawned,
            "p2_object_id": self.p2_object_id,
            "p1_position": self.p1_position,
            "current_room": self.current_room,
            "p1pos_count": self._p1pos_count,
        }


def run_cli(bridge: HadesMPBridge):
    """Interactive CLI for the bridge."""
    print()
    print("HadesMP Bridge CLI")
    print("Commands: ping, exec <lua>, send <msg>, status, nop, p2 <sub>, quit")
    print()

    while True:
        try:
            line = input("hadesmp> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        parts = line.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "quit" or cmd == "exit" or cmd == "q":
            break

        elif cmd == "ping":
            seq = bridge.ping()
            print(f"  sent PING (seq={seq}), waiting for PONG...")

        elif cmd == "exec":
            if not arg:
                print("  usage: exec <lua code>")
                continue
            seq = bridge.exec_lua(arg)
            print(f"  sent EXEC (seq={seq})")

        elif cmd == "send":
            if not arg:
                print("  usage: send <message>")
                continue
            seq = bridge.send_msg(arg)
            print(f"  sent MSG (seq={seq})")

        elif cmd == "nop":
            seq = bridge.send_nop()
            print(f"  sent NOP (seq={seq})")

        elif cmd == "status":
            s = bridge.status()
            print(f"  Lua version:    {s['lua_version'] or 'unknown'}")
            print(f"  Lua ready:      {s['lua_ready']}")
            print(f"  Heartbeats:     {s['heartbeats']}")
            print(f"  Last heartbeat: {s['last_heartbeat_ago']}")
            print(f"  Last RTT:       {s['last_rtt_ms']} ms")
            print(f"  Inbox seq:      {s['inbox_seq']}")
            print(f"  ACKed seqs:     {s['acked_seqs']}")
            print(f"  P2 spawned:     {s['p2_spawned']}")
            print(f"  Current room:   {s['current_room']}")
            print(f"  P1POS count:    {s['p1pos_count']}")

        elif cmd == "log":
            with bridge._lock:
                entries = bridge.message_log[-20:]
            if not entries:
                print("  (no messages)")
            for ts, mt, pl in entries:
                t = time.strftime("%H:%M:%S", time.localtime(ts))
                print(f"  {t} {mt}: {pl}")

        elif cmd == "p2":
            subcmd = arg.split(None, 1) if arg else []
            sub = subcmd[0].lower() if subcmd else ""
            subarg = subcmd[1] if len(subcmd) > 1 else ""

            if sub == "on":
                bridge.clear_p2_events()
                seq = bridge.p2_enable()
                print(f"  sent P2ENABLE:1 (seq={seq})")
            elif sub == "off":
                seq = bridge.p2_disable()
                print(f"  sent P2ENABLE:0 (seq={seq})")
            elif sub == "pos":
                parts = subarg.split(",")
                if len(parts) != 2:
                    print("  usage: p2 pos x,y")
                else:
                    try:
                        x, y = float(parts[0]), float(parts[1])
                        seq = bridge.p2_teleport(x, y)
                        print(f"  sent P2POS (seq={seq})")
                    except ValueError:
                        print("  error: x and y must be numbers")
            elif sub == "move":
                parts = subarg.split(",")
                if len(parts) != 2:
                    print("  usage: p2 move dx,dy")
                else:
                    try:
                        dx, dy = float(parts[0]), float(parts[1])
                        seq = bridge.p2_move(dx, dy)
                        print(f"  sent P2MOVE (seq={seq})")
                    except ValueError:
                        print("  error: dx and dy must be numbers")
            elif sub == "fire":
                weapon = subarg or "SwordWeapon"
                seq = bridge.p2_fire(weapon)
                print(f"  sent P2FIRE:{weapon} (seq={seq})")
            elif sub == "anim":
                if not subarg:
                    print("  usage: p2 anim <name>")
                else:
                    seq = bridge.p2_anim(subarg)
                    print(f"  sent P2ANIM:{subarg} (seq={seq})")
            elif sub == "test":
                print("  P2 quick test: enable → wait → move → fire → disable")
                bridge.clear_p2_events()
                bridge.p2_enable()
                evt = bridge.wait_p2_event("spawned", timeout=5.0)
                if evt:
                    print(f"    spawned: {evt}")
                    bridge.p2_move(50, 0)
                    time.sleep(0.3)
                    bridge.p2_fire("SwordWeapon")
                    time.sleep(0.5)
                    bridge.p2_disable()
                    print("    test complete")
                else:
                    print("    timeout waiting for spawn")
            elif sub == "status":
                s = bridge.status()
                print(f"  P2 spawned:     {s['p2_spawned']}")
                print(f"  P2 object ID:   {s['p2_object_id']}")
                print(f"  P1 position:    {s['p1_position']}")
                print(f"  Current room:   {s['current_room']}")
                print(f"  P1POS count:    {s['p1pos_count']}")
            else:
                print("  p2 subcommands: on, off, pos x,y, move dx,dy, fire [weapon],")
                print("                  anim <name>, test, status")

        elif cmd == "help":
            print("  ping           — send PING, measure RTT")
            print("  exec <lua>     — execute Lua code in game")
            print("  send <msg>     — send generic message")
            print("  nop            — send no-op (connectivity test)")
            print("  status         — show bridge status")
            print("  log            — show recent message log")
            print("  p2 <sub>       — P2 controller (on/off/pos/move/fire/anim/test/status)")
            print("  quit           — exit")

        else:
            print(f"  unknown command: {cmd} (type 'help' for commands)")


def main():
    parser = argparse.ArgumentParser(description="HadesMP IPC Bridge")
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=DEFAULT_GAME_DIR,
        help=f"Path to Hades x64Vk directory (default: {DEFAULT_GAME_DIR})",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Replay existing log from the beginning instead of tailing",
    )
    args = parser.parse_args()

    game_dir = args.game_dir.resolve()
    if not game_dir.is_dir():
        print(f"error: {game_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    bridge = HadesMPBridge(game_dir)

    if args.replay:
        # Start from beginning of file instead of end
        bridge.watcher._last_size = 0

    bridge.start()

    try:
        run_cli(bridge)
    finally:
        bridge.stop()
        print("[bridge] stopped")


if __name__ == "__main__":
    main()
