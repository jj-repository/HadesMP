#!/usr/bin/env python3
"""
HadesMP P2 Controller Integration Test

Automated test suite for the P2 controller protocol. Verifies:
  1. P2 enable/disable lifecycle
  2. P1POS position reports (~10Hz)
  3. P2POS absolute teleport
  4. P2MOVE relative movement
  5. P2FACE facing angle
  6. P2FIRE weapon fire
  7. P2ANIM animation set
  8. P2SYNC combined update

Prerequisites:
  - Game running, player in a room (start a run first)
  - Bridge log active (VERSION.dll proxy)

Usage:
    python3 test_p2.py [--game-dir /path/to/Hades/x64Vk]
"""

import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hadesmp_bridge import HadesMPBridge
from hadesmp_platform import detect_game_dir


class P2Test:
    """Sequential P2 controller test runner."""

    def __init__(self, bridge: HadesMPBridge, timeout: float = 5.0):
        self.bridge = bridge
        self.timeout = timeout
        self.results: list[dict] = []

    def run_test(self, name: str, fn) -> dict:
        """Run a named test function, catch exceptions."""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"{'='*60}")

        try:
            ok, detail = fn()
            result = {"name": name, "ok": ok, "detail": detail}
        except Exception as e:
            result = {"name": name, "ok": False, "detail": f"exception: {e}"}

        if result["ok"]:
            print(f"  PASS: {result['detail']}")
        else:
            print(f"  FAIL: {result['detail']}")

        self.results.append(result)
        return result

    def summary(self) -> bool:
        """Print summary, return True if all passed."""
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        passed = sum(1 for r in self.results if r["ok"])
        total = len(self.results)
        for r in self.results:
            status = "PASS" if r["ok"] else "FAIL"
            detail = r["detail"]
            if len(detail) > 80:
                detail = detail[:77] + "..."
            print(f"  [{status}] {r['name']}: {detail}")
        print(f"\n  {passed}/{total} tests passed")
        return passed == total


def wait_for_bridge(bridge: HadesMPBridge, timeout: float = 30.0) -> bool:
    """Wait until we see heartbeats."""
    print("[test] Waiting for game heartbeats...")
    start = time.time()
    initial_hb = bridge.heartbeat_count
    while time.time() - start < timeout:
        if bridge.heartbeat_count > initial_hb:
            print(f"[test] Bridge is live (HB count: {bridge.heartbeat_count})")
            return True
        time.sleep(0.5)
    print("[test] ERROR: No heartbeats. Is the game running in a room?")
    return False


def main():
    parser = argparse.ArgumentParser(description="HadesMP P2 Controller Integration Test")
    parser.add_argument(
        "--game-dir", type=Path, default=None,
        help="Path to Hades game subdirectory (auto-detected if omitted)",
    )
    parser.add_argument(
        "--timeout", type=float, default=5.0,
        help="Timeout per test in seconds (default: 5)",
    )
    parser.add_argument(
        "--skip-wait", action="store_true",
        help="Skip waiting for heartbeats",
    )
    args = parser.parse_args()

    if args.game_dir:
        game_dir = args.game_dir.resolve()
    else:
        try:
            config = detect_game_dir()
            game_dir = config.game_dir
            print(f"[test] auto-detected game dir: {game_dir}")
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)

    if not game_dir.is_dir():
        print(f"error: {game_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    bridge = HadesMPBridge(game_dir)
    bridge.start()

    try:
        if not args.skip_wait:
            if not wait_for_bridge(bridge):
                sys.exit(1)

        tester = P2Test(bridge, timeout=args.timeout)
        time.sleep(0.5)

        # ============================================================
        # Test 1: Enable P2
        # ============================================================
        def test_enable():
            bridge.clear_p2_events()
            bridge.p2_enable()
            # Wait for "enabled" event
            evt = bridge.wait_p2_event("enabled", timeout=3.0)
            if not evt:
                return False, "no 'enabled' event"
            # Wait for spawn (may take up to 1s due to room load delay)
            evt2 = bridge.wait_p2_event("spawned", timeout=5.0)
            if not evt2:
                return False, "enabled but no spawn event"
            return True, f"enabled + {evt2}"

        r = tester.run_test("P2 Enable + Spawn", test_enable)
        if not r["ok"]:
            print("\n[test] CRITICAL: P2 spawn failed — cannot continue.")
            tester.summary()
            sys.exit(1)

        time.sleep(0.5)

        # ============================================================
        # Test 2: P1POS reports arriving
        # ============================================================
        def test_p1pos():
            start_count = bridge._p1pos_count
            # Wait up to 2 seconds for at least 5 P1POS reports
            deadline = time.time() + 2.0
            while time.time() < deadline:
                if bridge._p1pos_count - start_count >= 5:
                    break
                time.sleep(0.1)
            count = bridge._p1pos_count - start_count
            if count < 3:
                return False, f"only {count} P1POS reports in 2s (expected >=3)"
            pos = bridge.p1_position
            if not pos:
                return False, "P1POS count ok but no position data"
            return True, f"{count} reports, P1 at ({pos[0]:.0f}, {pos[1]:.0f}, angle={pos[2]:.1f})"

        tester.run_test("P1POS reports (~10Hz)", test_p1pos)

        # ============================================================
        # Test 3: P2MOVE relative movement
        # ============================================================
        def test_p2move():
            # Send a relative move and check that no error event comes back
            bridge.clear_p2_events()
            bridge.p2_move(50, 30)
            time.sleep(0.3)
            # Check for errors
            err = bridge.wait_p2_event("err=", timeout=0.5)
            if err:
                return False, f"got error: {err}"
            return True, "moved by (50, 30) — no error"

        tester.run_test("P2MOVE relative movement", test_p2move)

        # ============================================================
        # Test 4: P2POS absolute teleport
        # ============================================================
        def test_p2pos():
            # Get P1 position to teleport P2 near it
            pos = bridge.p1_position
            if not pos:
                return False, "no P1 position available"
            target_x = pos[0] + 100
            target_y = pos[1] + 100
            bridge.clear_p2_events()
            bridge.p2_teleport(target_x, target_y)
            time.sleep(0.3)
            err = bridge.wait_p2_event("err=", timeout=0.5)
            if err:
                return False, f"got error: {err}"
            return True, f"teleported to ({target_x:.0f}, {target_y:.0f}) — no error"

        tester.run_test("P2POS absolute teleport", test_p2pos)

        # ============================================================
        # Test 5: P2FACE facing angle
        # ============================================================
        def test_p2face():
            bridge.clear_p2_events()
            bridge.p2_face(180.0)
            time.sleep(0.3)
            err = bridge.wait_p2_event("err=", timeout=0.5)
            if err:
                return False, f"got error: {err}"
            return True, "set facing to 180 degrees — no error"

        tester.run_test("P2FACE facing angle", test_p2face)

        # ============================================================
        # Test 6: P2FIRE weapon fire
        # ============================================================
        def test_p2fire():
            bridge.clear_p2_events()
            bridge.p2_fire("SwordWeapon")
            time.sleep(0.5)
            err = bridge.wait_p2_event("err=", timeout=0.5)
            if err:
                return False, f"got error: {err}"
            return True, "fired SwordWeapon — no error"

        tester.run_test("P2FIRE weapon fire", test_p2fire)

        # ============================================================
        # Test 7: P2ANIM animation
        # ============================================================
        def test_p2anim():
            bridge.clear_p2_events()
            bridge.p2_anim("EnemySwordIdle")
            time.sleep(0.3)
            err = bridge.wait_p2_event("err=", timeout=0.5)
            if err:
                return False, f"got error: {err}"
            return True, "set anim EnemySwordIdle — no error"

        tester.run_test("P2ANIM animation", test_p2anim)

        # ============================================================
        # Test 8: P2SYNC combined update
        # ============================================================
        def test_p2sync():
            pos = bridge.p1_position
            if not pos:
                return False, "no P1 position for sync target"
            bridge.clear_p2_events()
            bridge.p2_sync(pos[0] - 100, pos[1], 90.0, "EnemySwordIdle")
            time.sleep(0.3)
            err = bridge.wait_p2_event("err=", timeout=0.5)
            if err:
                return False, f"got error: {err}"
            return True, f"synced to ({pos[0]-100:.0f}, {pos[1]:.0f}, 90deg, EnemySwordIdle)"

        tester.run_test("P2SYNC combined update", test_p2sync)

        # ============================================================
        # Test 9: Disable P2
        # ============================================================
        def test_disable():
            bridge.clear_p2_events()
            bridge.p2_disable()
            # Wait for disabled event
            evt = bridge.wait_p2_event("despawned", timeout=3.0)
            if not evt:
                # May have already been destroyed — check for disabled
                evt2 = bridge.wait_p2_event("disabled", timeout=1.0)
                if evt2:
                    return True, "disabled (no despawn — may have been cleaned up)"
                return False, "no despawn/disable event"
            return True, f"disabled + {evt}"

        tester.run_test("P2 Disable + Despawn", test_disable)

        # Verify P2 state is cleared
        time.sleep(0.3)
        if bridge.p2_spawned:
            print("  WARNING: bridge still thinks P2 is spawned")

        # ============================================================
        # Test 10: Re-enable to verify lifecycle works
        # ============================================================
        def test_reenable():
            bridge.clear_p2_events()
            bridge.p2_enable()
            evt = bridge.wait_p2_event("spawned", timeout=5.0)
            if not evt:
                return False, "re-enable spawn failed"
            # Disable again for cleanup
            bridge.clear_p2_events()
            bridge.p2_disable()
            evt2 = bridge.wait_p2_event("disabled", timeout=3.0)
            despawn = bridge.wait_p2_event("despawned", timeout=1.0)
            return True, f"re-spawned ({evt}), then disabled"

        tester.run_test("P2 Re-enable lifecycle", test_reenable)

        # Print summary
        all_pass = tester.summary()
        sys.exit(0 if all_pass else 1)

    except KeyboardInterrupt:
        print("\n[test] Interrupted")
        # Cleanup: disable P2
        try:
            bridge.p2_disable()
            time.sleep(0.3)
        except Exception:
            pass
    finally:
        bridge.stop()
        print("[test] Bridge stopped")


if __name__ == "__main__":
    main()
