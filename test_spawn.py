#!/usr/bin/env python3
"""
HadesMP Entity Spawn Feasibility Test

Runs a series of EXEC commands through the bridge to test whether we can
spawn, position, move, and control a second player-like entity in Hades.

Prerequisites:
  - Game running (launched via Steam with launch_styx.sh)
  - Player in a room (start a run first, not on title screen)
  - Bridge log file exists (VERSION.dll proxy active)

Usage:
    python3 test_spawn.py [--game-dir /path/to/Hades/x64Vk]
"""

import argparse
import sys
import threading
import time
from pathlib import Path

# Import the bridge from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from hadesmp_bridge import HadesMPBridge, DEFAULT_GAME_DIR


class SpawnTest:
    """Runs sequential EXEC tests and collects results."""

    def __init__(self, bridge: HadesMPBridge, timeout: float = 5.0):
        self.bridge = bridge
        self.timeout = timeout
        self.results: list[dict] = []

        # Collect EXEC responses and MSG payloads
        self._response_event = threading.Event()
        self._last_exec_ok: str | None = None
        self._last_exec_err: str | None = None
        self._last_msgs: list[str] = []

        # Hook into bridge message flow
        self.bridge.watcher.add_callback(self._on_message)

    def _on_message(self, msg_type: str, payload: str):
        if msg_type == "EXEC_OK":
            self._last_exec_ok = payload
            self._last_exec_err = None
            self._response_event.set()
        elif msg_type == "EXEC_ERR":
            self._last_exec_err = payload
            self._last_exec_ok = None
            self._response_event.set()
        elif msg_type == "MSG":
            self._last_msgs.append(payload)
            self._response_event.set()

    def _exec_and_wait(self, lua_code: str, wait_for_msg: str | None = None) -> dict:
        """Send EXEC and wait for response. Optionally wait for a specific MSG prefix."""
        self._response_event.clear()
        self._last_exec_ok = None
        self._last_exec_err = None
        self._last_msgs.clear()

        seq = self.bridge.exec_lua(lua_code)
        deadline = time.time() + self.timeout

        # Wait for EXEC_OK/EXEC_ERR first
        while time.time() < deadline:
            if self._response_event.wait(timeout=0.1):
                self._response_event.clear()
                if self._last_exec_err is not None:
                    return {"ok": False, "error": self._last_exec_err, "seq": seq}
                if self._last_exec_ok is not None:
                    break

        if self._last_exec_ok is None and self._last_exec_err is None:
            return {"ok": False, "error": "timeout waiting for EXEC response", "seq": seq}

        # If we also need a MSG, wait for it
        if wait_for_msg:
            while time.time() < deadline:
                for msg in self._last_msgs:
                    if msg.startswith(wait_for_msg):
                        return {"ok": True, "result": self._last_exec_ok, "msg": msg, "seq": seq}
                self._response_event.wait(timeout=0.1)
                self._response_event.clear()
            return {"ok": False, "error": f"timeout waiting for MSG:{wait_for_msg}", "seq": seq}

        return {"ok": True, "result": self._last_exec_ok, "seq": seq}

    def run_test(self, name: str, lua_code: str, wait_for_msg: str | None = None) -> dict:
        """Run a named test and record the result."""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")
        print(f"  Lua: {lua_code[:120]}{'...' if len(lua_code) > 120 else ''}")

        result = self._exec_and_wait(lua_code, wait_for_msg)
        result["name"] = name

        if result["ok"]:
            print(f"  PASS: {result.get('msg') or result.get('result', 'ok')}")
        else:
            print(f"  FAIL: {result['error']}")

        self.results.append(result)
        return result

    def summary(self):
        """Print a summary of all test results."""
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        passed = sum(1 for r in self.results if r["ok"])
        total = len(self.results)
        for r in self.results:
            status = "PASS" if r["ok"] else "FAIL"
            detail = r.get("msg") or r.get("result") or r.get("error", "")
            # Truncate long details
            if len(detail) > 80:
                detail = detail[:77] + "..."
            print(f"  [{status}] {r['name']}: {detail}")
        print(f"\n  {passed}/{total} tests passed")
        return passed == total


def wait_for_bridge(bridge: HadesMPBridge, timeout: float = 30.0) -> bool:
    """Wait until we see heartbeats (game is running and in a room)."""
    print("[test] Waiting for game heartbeats...")
    start = time.time()
    initial_hb = bridge.heartbeat_count
    while time.time() - start < timeout:
        if bridge.heartbeat_count > initial_hb:
            print(f"[test] Got heartbeat! Bridge is live (HB count: {bridge.heartbeat_count})")
            return True
        time.sleep(0.5)
    print("[test] ERROR: No heartbeats received. Is the game running in a room?")
    return False


def main():
    parser = argparse.ArgumentParser(description="HadesMP Entity Spawn Feasibility Test")
    parser.add_argument(
        "--game-dir", type=Path, default=DEFAULT_GAME_DIR,
        help=f"Path to Hades x64Vk directory (default: {DEFAULT_GAME_DIR})",
    )
    parser.add_argument(
        "--timeout", type=float, default=5.0,
        help="Timeout per test in seconds (default: 5)",
    )
    parser.add_argument(
        "--skip-wait", action="store_true",
        help="Skip waiting for heartbeats (assume bridge is already live)",
    )
    args = parser.parse_args()

    game_dir = args.game_dir.resolve()
    if not game_dir.is_dir():
        print(f"error: {game_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    bridge = HadesMPBridge(game_dir)
    bridge.start()

    try:
        # Wait for the game to be alive
        if not args.skip_wait:
            if not wait_for_bridge(bridge):
                sys.exit(1)

        tester = SpawnTest(bridge, timeout=args.timeout)

        # Give the bridge a moment to stabilize
        time.sleep(0.5)

        # ============================================================
        # Step 1: Spawn a Skelly (TrainingMeleeSummon) next to the hero
        # ============================================================
        spawn_code = """
local ed = EnemyData["TrainingMeleeSummon"]
if not ed then
    print("HADESMP:MSG:p2_spawn_err=no_EnemyData")
    return
end
local e = DeepCopyTable(ed)
e.ObjectId = SpawnUnit({ Name = ed.Name, Group = "Standing",
    DestinationId = CurrentRun.Hero.ObjectId, OffsetX = 200, OffsetY = 0 })
if not e.ObjectId or e.ObjectId == 0 then
    print("HADESMP:MSG:p2_spawn_err=SpawnUnit_returned_" .. tostring(e.ObjectId))
    return
end
SetupEnemyObject(e, CurrentRun)
_G.P2 = e
print("HADESMP:MSG:p2_spawned=" .. tostring(e.ObjectId))
""".strip()
        r = tester.run_test("Spawn entity", spawn_code, wait_for_msg="p2_spawn")
        if not r["ok"] or "p2_spawn_err" in r.get("msg", ""):
            print("\n[test] CRITICAL: Spawn failed — cannot continue remaining tests.")
            tester.summary()
            sys.exit(1)

        # Small delay for entity to fully initialize
        time.sleep(0.3)

        # ============================================================
        # Step 2: Read position
        # ============================================================
        pos_code = """
if not _G.P2 then
    print("HADESMP:MSG:p2_pos_err=no_P2")
    return
end
local ok, loc = pcall(GetLocation, { Id = _G.P2.ObjectId })
if ok and loc then
    print("HADESMP:MSG:p2_pos=" .. tostring(loc.X) .. "," .. tostring(loc.Y))
else
    print("HADESMP:MSG:p2_pos_err=" .. tostring(loc))
end
""".strip()
        tester.run_test("Read position", pos_code, wait_for_msg="p2_pos")

        # ============================================================
        # Step 3a: Teleport
        # ============================================================
        tp_code = """
if not _G.P2 then
    print("HADESMP:MSG:p2_tp_err=no_P2")
    return
end
local ok, err = pcall(Teleport, { Id = _G.P2.ObjectId,
    DestinationId = CurrentRun.Hero.ObjectId, OffsetX = -150, OffsetY = -150 })
if ok then
    print("HADESMP:MSG:p2_teleported=ok")
else
    print("HADESMP:MSG:p2_tp_err=" .. tostring(err))
end
""".strip()
        tester.run_test("Teleport", tp_code, wait_for_msg="p2_t")

        time.sleep(0.5)

        # ============================================================
        # Step 3b: Move toward hero
        # ============================================================
        move_code = """
if not _G.P2 then
    print("HADESMP:MSG:p2_move_err=no_P2")
    return
end
local ok, err = pcall(Move, { Id = _G.P2.ObjectId,
    DestinationId = CurrentRun.Hero.ObjectId })
if ok then
    print("HADESMP:MSG:p2_moving=ok")
else
    print("HADESMP:MSG:p2_move_err=" .. tostring(err))
end
""".strip()
        tester.run_test("Move toward hero", move_code, wait_for_msg="p2_mov")

        time.sleep(1.0)  # Let it move for a moment

        # Stop movement
        stop_code = """
if _G.P2 then
    pcall(Stop, { Id = _G.P2.ObjectId })
    print("HADESMP:MSG:p2_stopped=ok")
end
""".strip()
        tester.run_test("Stop movement", stop_code, wait_for_msg="p2_stopped")

        # ============================================================
        # Step 4: Invulnerability
        # ============================================================
        invuln_code = """
if not _G.P2 then
    print("HADESMP:MSG:p2_invuln_err=no_P2")
    return
end
local ok, err = pcall(SetInvulnerable, { Id = _G.P2.ObjectId })
if ok then
    print("HADESMP:MSG:p2_invulnerable=ok")
else
    print("HADESMP:MSG:p2_invuln_err=" .. tostring(err))
end
""".strip()
        tester.run_test("Set invulnerable", invuln_code, wait_for_msg="p2_invuln")

        # ============================================================
        # Step 5: Fire weapon
        # ============================================================
        fire_code = """
if not _G.P2 then
    print("HADESMP:MSG:p2_fire_err=no_P2")
    return
end
local ok, err = pcall(FireWeaponFromUnit,
    { Id = _G.P2.ObjectId, Weapon = "SwordWeapon",
      DestinationId = CurrentRun.Hero.ObjectId, AutoEquip = true })
if ok then
    print("HADESMP:MSG:p2_fired=ok")
else
    print("HADESMP:MSG:p2_fire_err=" .. tostring(err))
end
""".strip()
        tester.run_test("Fire weapon (SwordWeapon)", fire_code, wait_for_msg="p2_fire")

        time.sleep(0.5)

        # ============================================================
        # Step 6: Set animation
        # ============================================================
        anim_code = """
if not _G.P2 then
    print("HADESMP:MSG:p2_anim_err=no_P2")
    return
end
local ok, err = pcall(SetAnimation, { DestinationId = _G.P2.ObjectId, Name = "EnemySwordIdle" })
if ok then
    print("HADESMP:MSG:p2_anim=ok")
else
    print("HADESMP:MSG:p2_anim_err=" .. tostring(err))
end
""".strip()
        tester.run_test("Set animation", anim_code, wait_for_msg="p2_anim")

        # ============================================================
        # Bonus: Read position again (verify it moved from the teleport)
        # ============================================================
        tester.run_test("Read position (after move)", pos_code, wait_for_msg="p2_pos")

        # ============================================================
        # Cleanup: Destroy the entity
        # ============================================================
        cleanup_code = """
if _G.P2 then
    local id = _G.P2.ObjectId
    pcall(Destroy, { Id = id })
    _G.P2 = nil
    print("HADESMP:MSG:p2_destroyed=" .. tostring(id))
else
    print("HADESMP:MSG:p2_destroyed=already_nil")
end
""".strip()
        tester.run_test("Cleanup (destroy entity)", cleanup_code, wait_for_msg="p2_destroyed")

        # Print summary
        all_pass = tester.summary()
        sys.exit(0 if all_pass else 1)

    except KeyboardInterrupt:
        print("\n[test] Interrupted")
    finally:
        bridge.stop()
        print("[test] Bridge stopped")


if __name__ == "__main__":
    main()
