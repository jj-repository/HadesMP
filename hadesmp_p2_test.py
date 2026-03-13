#!/usr/bin/env python3
"""
HadesMP P2 Keyboard Test — real-time control of the P2 entity.

Uses evdev to capture keyboard input globally (works while game has focus).
Game stays focused and unpaused; this script reads keypresses in the background.

WASD: move P2         1-6: fire weapons       Q: quit
Arrow keys: move P2   Space: sword attack      E: toggle P2 on/off

Prerequisites:
  - Game running, player in a room
  - Bridge log active (VERSION.dll proxy)
  - User in 'input' group (sudo usermod -aG input $USER) or run with sudo

Usage:
    python3 hadesmp_p2_test.py [--game-dir /path/to/Hades/x64Vk] [--device /dev/input/eventN]
"""

import argparse
import selectors
import sys
import time
from pathlib import Path

try:
    import evdev
    from evdev import ecodes
except ImportError:
    print("error: evdev not installed — run: pip install evdev", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from hadesmp_bridge import HadesMPBridge, DEFAULT_GAME_DIR

MOVE_STEP = 30  # pixels per keypress

# evdev key code → action mapping
KEY_ACTIONS = {
    ecodes.KEY_W: "up",
    ecodes.KEY_A: "left",
    ecodes.KEY_S: "down",
    ecodes.KEY_D: "right",
    ecodes.KEY_UP: "up",
    ecodes.KEY_LEFT: "left",
    ecodes.KEY_DOWN: "down",
    ecodes.KEY_RIGHT: "right",
    ecodes.KEY_SPACE: "fire_sword",
    ecodes.KEY_1: "fire_1",
    ecodes.KEY_2: "fire_2",
    ecodes.KEY_3: "fire_3",
    ecodes.KEY_4: "fire_4",
    ecodes.KEY_5: "fire_5",
    ecodes.KEY_6: "fire_6",
    ecodes.KEY_E: "toggle",
    ecodes.KEY_P: "p1pos",
    ecodes.KEY_R: "room",
    ecodes.KEY_Q: "quit",
}

WEAPON_MAP = {
    "fire_1": "SwordWeapon",
    "fire_2": "BowWeapon",
    "fire_3": "SpearWeapon",
    "fire_4": "ShieldWeapon",
    "fire_5": "FistWeapon",
    "fire_6": "GunWeapon",
    "fire_sword": "SwordWeapon",
}

# Movement actions and their deltas
MOVE_DELTAS = {
    "up": (0, -MOVE_STEP),
    "down": (0, MOVE_STEP),
    "left": (-MOVE_STEP, 0),
    "right": (MOVE_STEP, 0),
}


def find_keyboard() -> str | None:
    """Auto-detect a keyboard device from /dev/input/.

    Filters out mice (EV_REL) and requires F-keys to distinguish real keyboards
    from mice/gamepads that also report some key events.
    """
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    candidates = []
    for dev in devices:
        caps = dev.capabilities(verbose=False)
        if ecodes.EV_KEY not in caps:
            continue
        # Mice have EV_REL (relative axes) — skip them
        if ecodes.EV_REL in caps:
            continue
        keys = caps[ecodes.EV_KEY]
        # Real keyboards have alpha keys + F-keys + number row
        has_alpha = ecodes.KEY_A in keys and ecodes.KEY_Z in keys
        has_fkeys = ecodes.KEY_F1 in keys and ecodes.KEY_F12 in keys
        has_numrow = ecodes.KEY_1 in keys and ecodes.KEY_0 in keys
        if has_alpha and has_fkeys and has_numrow:
            candidates.append((dev.path, dev.name, len(keys)))
    if not candidates:
        return None
    # Prefer the device with the most keys (most likely the real keyboard)
    candidates.sort(key=lambda x: x[2], reverse=True)
    print(f"[test] Found keyboards:")
    for path, name, nkeys in candidates:
        print(f"  {path}: {name} ({nkeys} keys)")
    return candidates[0][0]


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
    parser = argparse.ArgumentParser(description="HadesMP P2 Keyboard Test (evdev)")
    parser.add_argument(
        "--game-dir", type=Path, default=DEFAULT_GAME_DIR,
        help=f"Path to Hades x64Vk directory (default: {DEFAULT_GAME_DIR})",
    )
    parser.add_argument(
        "--device", type=str, default=None,
        help="Input device path (e.g. /dev/input/event3). Auto-detected if omitted.",
    )
    parser.add_argument(
        "--step", type=int, default=MOVE_STEP,
        help=f"Pixels per movement keypress (default: {MOVE_STEP})",
    )
    args = parser.parse_args()

    game_dir = args.game_dir.resolve()
    if not game_dir.is_dir():
        print(f"error: {game_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Find keyboard device
    dev_path = args.device
    if not dev_path:
        dev_path = find_keyboard()
        if not dev_path:
            print("error: no keyboard found in /dev/input/", file=sys.stderr)
            print("  try: --device /dev/input/eventN", file=sys.stderr)
            print("  or:  sudo usermod -aG input $USER (then re-login)", file=sys.stderr)
            sys.exit(1)

    try:
        kbd = evdev.InputDevice(dev_path)
    except PermissionError:
        print(f"error: no permission to read {dev_path}", file=sys.stderr)
        print("  fix: sudo usermod -aG input $USER (then re-login)", file=sys.stderr)
        print("  or:  run this script with sudo", file=sys.stderr)
        sys.exit(1)

    print(f"[test] Using keyboard: {kbd.name} ({kbd.path})")

    step = args.step
    move_deltas = {
        "up": (0, -step),
        "down": (0, step),
        "left": (-step, 0),
        "right": (step, 0),
    }

    bridge = HadesMPBridge(game_dir)
    bridge.start()

    if not wait_for_bridge(bridge):
        bridge.stop()
        sys.exit(1)

    # Enable P2
    print("[test] Enabling P2...")
    bridge.clear_p2_events()
    bridge.p2_enable()
    evt = bridge.wait_p2_event("spawned", timeout=5.0)
    if evt:
        print(f"[test] P2 spawned: {evt}")
    else:
        print("[test] Warning: no spawn event within 5s (may need to wait for room)")

    p2_active = True

    print()
    print("=" * 55)
    print("  P2 Keyboard Control (evdev — works in background)")
    print("=" * 55)
    print("  WASD / Arrow keys: move P2")
    print("  1-6: fire weapon (Sword/Bow/Spear/Shield/Fist/Gun)")
    print("  Space: sword attack")
    print("  E: toggle P2 on/off")
    print("  P: print P1 position")
    print("  R: print current room")
    print("  Q: quit")
    print("=" * 55)
    print()
    print("  Game can stay focused — input is captured globally.")
    print("  Press Q (on keyboard) to stop.\n")

    # Track held keys for repeat movement
    held_moves: set[str] = set()
    last_move_time = 0.0
    MOVE_REPEAT_INTERVAL = 0.05  # 20Hz repeat rate for held keys

    try:
        sel = selectors.DefaultSelector()
        sel.register(kbd, selectors.EVENT_READ)

        running = True
        while running:
            # Check for input events (with short timeout for held-key repeating)
            events = sel.select(timeout=MOVE_REPEAT_INTERVAL)

            for key, mask in events:
                for event in kbd.read():
                    if event.type != ecodes.EV_KEY:
                        continue

                    action = KEY_ACTIONS.get(event.code)
                    if not action:
                        continue

                    # Key down (1) or repeat (2)
                    if event.value in (1, 2):
                        if action == "quit":
                            running = False
                            break

                        elif action in move_deltas:
                            held_moves.add(action)
                            dx, dy = move_deltas[action]
                            bridge.p2_move(dx, dy)

                        elif action.startswith("fire_"):
                            weapon = WEAPON_MAP[action]
                            bridge.p2_fire(weapon)

                        elif action == "toggle" and event.value == 1:
                            if p2_active:
                                bridge.p2_disable()
                                p2_active = False
                                print("[test] P2 disabled")
                            else:
                                bridge.clear_p2_events()
                                bridge.p2_enable()
                                p2_active = True
                                print("[test] P2 enabled")

                        elif action == "p1pos" and event.value == 1:
                            pos = bridge.p1_position
                            if pos:
                                print(f"[P1] x={pos[0]:.0f} y={pos[1]:.0f} angle={pos[2]:.1f}")
                            else:
                                print("[P1] no position data")

                        elif action == "room" and event.value == 1:
                            print(f"[room] {bridge.current_room or 'unknown'}")

                    # Key up (0)
                    elif event.value == 0:
                        if action in move_deltas:
                            held_moves.discard(action)

                if not running:
                    break

            # Repeat movement for held keys
            now = time.time()
            if held_moves and now - last_move_time >= MOVE_REPEAT_INTERVAL:
                last_move_time = now
                # Combine all held directions into one move
                total_dx, total_dy = 0, 0
                for action in held_moves:
                    dx, dy = move_deltas[action]
                    total_dx += dx
                    total_dy += dy
                if total_dx != 0 or total_dy != 0:
                    bridge.p2_move(total_dx, total_dy)

    except KeyboardInterrupt:
        print("\n[test] Interrupted")
    finally:
        sel.close()
        kbd.close()

        if p2_active:
            print("[test] Disabling P2...")
            bridge.p2_disable()
            time.sleep(0.5)

        bridge.stop()
        print("[test] Done")


if __name__ == "__main__":
    main()
