#!/usr/bin/env python3
"""
HadesMP P2 Keyboard Test — real-time control of the P2 entity.

On Linux: uses evdev for global keyboard capture (works while game has focus).
On Windows/WSL2: uses pynput for keyboard capture.

WASD: move P2         1-6: fire weapons       Q: quit
Arrow keys: move P2   Space: sword attack      E: toggle P2 on/off

Prerequisites:
  - Game running, player in a room
  - Bridge log active (VERSION.dll proxy)
  - Linux: user in 'input' group or run with sudo
  - Windows: pip install pynput

Usage:
    python3 hadesmp_p2_test.py [--game-dir /path/to/Hades/x64] [--device /dev/input/eventN]
"""

import argparse
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hadesmp_bridge import HadesMPBridge
from hadesmp_platform import detect_game_dir, detect_platform

# Detect input backend
BACKEND = None
evdev = None
pynput_keyboard = None

_plat = detect_platform()
if _plat == "linux":
    try:
        import evdev as _evdev
        evdev = _evdev
        from evdev import ecodes
        BACKEND = "evdev"
    except ImportError:
        pass
if BACKEND is None and _plat in ("windows", "wsl2"):
    if _plat == "wsl2":
        print("warning: keyboard capture from WSL2 requires native Windows Python + pynput",
              file=sys.stderr)
        print("  run this script from Windows Python, or use evdev on native Linux",
              file=sys.stderr)
    try:
        from pynput import keyboard as _pynput_kb
        pynput_keyboard = _pynput_kb
        BACKEND = "pynput"
    except ImportError:
        pass
if BACKEND is None and _plat == "linux":
    print("error: no input backend available", file=sys.stderr)
    print("  Linux: pip install evdev", file=sys.stderr)
    print("  Windows: pip install pynput", file=sys.stderr)
    sys.exit(1)
if BACKEND is None:
    print("error: no input backend available — pip install pynput", file=sys.stderr)
    sys.exit(1)

MOVE_STEP = 30  # pixels per keypress

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

# evdev key mapping (only when backend is evdev)
if BACKEND == "evdev":
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

# pynput key mapping (only when backend is pynput)
if BACKEND == "pynput":
    from pynput.keyboard import Key, KeyCode
    PYNPUT_KEY_ACTIONS = {
        KeyCode.from_char('w'): "up",
        KeyCode.from_char('a'): "left",
        KeyCode.from_char('s'): "down",
        KeyCode.from_char('d'): "right",
        Key.up: "up",
        Key.left: "left",
        Key.down: "down",
        Key.right: "right",
        Key.space: "fire_sword",
        KeyCode.from_char('1'): "fire_1",
        KeyCode.from_char('2'): "fire_2",
        KeyCode.from_char('3'): "fire_3",
        KeyCode.from_char('4'): "fire_4",
        KeyCode.from_char('5'): "fire_5",
        KeyCode.from_char('6'): "fire_6",
        KeyCode.from_char('e'): "toggle",
        KeyCode.from_char('p'): "p1pos",
        KeyCode.from_char('r'): "room",
        KeyCode.from_char('q'): "quit",
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


def _run_evdev_loop(bridge, move_deltas, p2_active_ref):
    """Input loop using evdev (Linux)."""
    import selectors

    dev_path = bridge._evdev_device
    kbd = evdev.InputDevice(dev_path)
    print(f"[test] Using keyboard: {kbd.name} ({kbd.path})")

    held_moves: set[str] = set()
    last_move_time = 0.0
    MOVE_REPEAT_INTERVAL = 0.05

    sel = selectors.DefaultSelector()
    sel.register(kbd, selectors.EVENT_READ)

    try:
        running = True
        while running:
            events = sel.select(timeout=MOVE_REPEAT_INTERVAL)

            for key, mask in events:
                for event in kbd.read():
                    if event.type != ecodes.EV_KEY:
                        continue

                    action = KEY_ACTIONS.get(event.code)
                    if not action:
                        continue

                    if event.value in (1, 2):
                        if action == "quit":
                            running = False
                            break
                        elif action in move_deltas:
                            held_moves.add(action)
                            dx, dy = move_deltas[action]
                            bridge.p2_move(dx, dy)
                        elif action.startswith("fire_"):
                            bridge.p2_fire(WEAPON_MAP[action])
                        elif action == "toggle" and event.value == 1:
                            if p2_active_ref[0]:
                                bridge.p2_disable()
                                p2_active_ref[0] = False
                                print("[test] P2 disabled")
                            else:
                                bridge.clear_p2_events()
                                bridge.p2_enable()
                                p2_active_ref[0] = True
                                print("[test] P2 enabled")
                        elif action == "p1pos" and event.value == 1:
                            pos = bridge.p1_position
                            if pos:
                                print(f"[P1] x={pos[0]:.0f} y={pos[1]:.0f} angle={pos[2]:.1f}")
                            else:
                                print("[P1] no position data")
                        elif action == "room" and event.value == 1:
                            print(f"[room] {bridge.current_room or 'unknown'}")

                    elif event.value == 0:
                        if action in move_deltas:
                            held_moves.discard(action)

                    if not running:
                        break

            now = time.time()
            if held_moves and now - last_move_time >= MOVE_REPEAT_INTERVAL:
                last_move_time = now
                total_dx, total_dy = 0, 0
                for action in held_moves:
                    dx, dy = move_deltas[action]
                    total_dx += dx
                    total_dy += dy
                if total_dx != 0 or total_dy != 0:
                    bridge.p2_move(total_dx, total_dy)
    finally:
        sel.close()
        kbd.close()


def _run_pynput_loop(bridge, move_deltas, p2_active_ref):
    """Input loop using pynput (Windows)."""
    import threading

    held_moves: set[str] = set()
    running_event = threading.Event()

    def on_press(key):
        action = PYNPUT_KEY_ACTIONS.get(key)
        if not action:
            return
        if action == "quit":
            running_event.set()
            return False  # Stop listener
        elif action in move_deltas:
            held_moves.add(action)
            dx, dy = move_deltas[action]
            bridge.p2_move(dx, dy)
        elif action.startswith("fire_"):
            bridge.p2_fire(WEAPON_MAP[action])
        elif action == "toggle":
            if p2_active_ref[0]:
                bridge.p2_disable()
                p2_active_ref[0] = False
                print("[test] P2 disabled")
            else:
                bridge.clear_p2_events()
                bridge.p2_enable()
                p2_active_ref[0] = True
                print("[test] P2 enabled")
        elif action == "p1pos":
            pos = bridge.p1_position
            if pos:
                print(f"[P1] x={pos[0]:.0f} y={pos[1]:.0f} angle={pos[2]:.1f}")
            else:
                print("[P1] no position data")
        elif action == "room":
            print(f"[room] {bridge.current_room or 'unknown'}")

    def on_release(key):
        action = PYNPUT_KEY_ACTIONS.get(key)
        if action and action in move_deltas:
            held_moves.discard(action)

    listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    MOVE_REPEAT_INTERVAL = 0.05
    last_move_time = 0.0

    try:
        while not running_event.is_set():
            now = time.time()
            if held_moves and now - last_move_time >= MOVE_REPEAT_INTERVAL:
                last_move_time = now
                total_dx, total_dy = 0, 0
                for action in held_moves:
                    dx, dy = move_deltas[action]
                    total_dx += dx
                    total_dy += dy
                if total_dx != 0 or total_dy != 0:
                    bridge.p2_move(total_dx, total_dy)
            time.sleep(MOVE_REPEAT_INTERVAL)
    finally:
        listener.stop()


def main():
    parser = argparse.ArgumentParser(description="HadesMP P2 Keyboard Test")
    parser.add_argument(
        "--game-dir", type=Path, default=None,
        help="Path to Hades game subdirectory (auto-detected if omitted)",
    )
    parser.add_argument(
        "--device", type=str, default=None,
        help="Input device path for evdev (e.g. /dev/input/event3). Auto-detected if omitted.",
    )
    parser.add_argument(
        "--step", type=int, default=MOVE_STEP,
        help=f"Pixels per movement keypress (default: {MOVE_STEP})",
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

    # For evdev, resolve keyboard device
    if BACKEND == "evdev":
        dev_path = args.device
        if not dev_path:
            dev_path = find_keyboard()
            if not dev_path:
                print("error: no keyboard found in /dev/input/", file=sys.stderr)
                print("  try: --device /dev/input/eventN", file=sys.stderr)
                print("  or:  sudo usermod -aG input $USER (then re-login)", file=sys.stderr)
                sys.exit(1)
        try:
            test_dev = evdev.InputDevice(dev_path)
            test_dev.close()
        except PermissionError:
            print(f"error: no permission to read {dev_path}", file=sys.stderr)
            print("  fix: sudo usermod -aG input $USER (then re-login)", file=sys.stderr)
            print("  or:  run this script with sudo", file=sys.stderr)
            sys.exit(1)

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

    p2_active = [True]  # mutable ref for callbacks

    print()
    print("=" * 55)
    backend_label = "evdev" if BACKEND == "evdev" else "pynput"
    print(f"  P2 Keyboard Control ({backend_label} — works in background)")
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

    try:
        if BACKEND == "evdev":
            bridge._evdev_device = dev_path
            _run_evdev_loop(bridge, move_deltas, p2_active)
        elif BACKEND == "pynput":
            _run_pynput_loop(bridge, move_deltas, p2_active)
    except KeyboardInterrupt:
        print("\n[test] Interrupted")
    finally:
        if p2_active[0]:
            print("[test] Disabling P2...")
            bridge.p2_disable()
            time.sleep(0.5)

        bridge.stop()
        print("[test] Done")


if __name__ == "__main__":
    main()
