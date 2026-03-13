#!/bin/bash
# Build and install HadesMP proxy DLLs (Linux/Wine)
set -e

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Auto-detect Hades install via Steam library folders
find_hades() {
    local steam_dirs=(
        "$HOME/.local/share/Steam/steamapps"
        "$HOME/.steam/steam/steamapps"
    )
    # Also check libraryfolders.vdf for extra library paths
    for base in "${steam_dirs[@]}"; do
        local vdf="$base/libraryfolders.vdf"
        if [ -f "$vdf" ]; then
            while IFS= read -r line; do
                local path
                path=$(echo "$line" | grep -oP '"path"\s+"\K[^"]+')
                if [ -n "$path" ]; then
                    steam_dirs+=("$path/steamapps")
                fi
            done < "$vdf"
        fi
    done

    for dir in "${steam_dirs[@]}"; do
        local candidate="$dir/common/Hades"
        if [ -d "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

find_wine_prefix() {
    local steam_dirs=(
        "$HOME/.local/share/Steam/steamapps"
        "$HOME/.steam/steam/steamapps"
    )
    for base in "${steam_dirs[@]}"; do
        local vdf="$base/libraryfolders.vdf"
        if [ -f "$vdf" ]; then
            while IFS= read -r line; do
                local path
                path=$(echo "$line" | grep -oP '"path"\s+"\K[^"]+')
                if [ -n "$path" ]; then
                    steam_dirs+=("$path/steamapps")
                fi
            done < "$vdf"
        fi
    done

    for dir in "${steam_dirs[@]}"; do
        local candidate="$dir/compatdata/1145360/pfx"
        if [ -d "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# Allow override via environment
HADES_ROOT="${HADES_ROOT:-$(find_hades 2>/dev/null || true)}"
WINE_PREFIX="${WINE_PREFIX:-$(find_wine_prefix 2>/dev/null || true)}"

if [ -z "$HADES_ROOT" ]; then
    echo "[!] Could not find Hades install. Set HADES_ROOT:"
    echo "    HADES_ROOT=/path/to/Hades ./build_dll.sh"
    exit 1
fi
echo "[*] Hades: $HADES_ROOT"

# Determine game subdirectory (x64Vk for Vulkan/Proton, x64 otherwise)
GAME_DIR="$HADES_ROOT/x64Vk"
if [ ! -d "$GAME_DIR" ]; then
    GAME_DIR="$HADES_ROOT/x64"
fi

echo ""
echo "=== Building stdout_redirect.dll ==="
x86_64-w64-mingw32-gcc -shared -o "$SCRIPT_DIR/stdout_redirect.dll" \
    "$SCRIPT_DIR/stdout_redirect.c" \
    -Wl,--subsystem,windows -O2
echo "Built: stdout_redirect.dll"

echo ""
echo "=== Building lua52.dll (proxy) ==="
x86_64-w64-mingw32-gcc -shared -o "$SCRIPT_DIR/lua52.dll" \
    "$SCRIPT_DIR/lua52_proxy.c" "$SCRIPT_DIR/lua52.def" -O2
echo "Built: lua52.dll"

echo ""
echo "=== Building VERSION.dll (proxy) ==="
x86_64-w64-mingw32-gcc -shared -o "$SCRIPT_DIR/VERSION.dll" \
    "$SCRIPT_DIR/version_proxy.c" -O2
echo "Built: VERSION.dll"

echo ""
echo "=== Installing to game directory ==="
cp "$SCRIPT_DIR/VERSION.dll" "$GAME_DIR/VERSION.dll"
echo "Installed: $GAME_DIR/VERSION.dll"

# lua52 proxy: back up original first
if [ ! -f "$GAME_DIR/lua52_original.dll" ] && [ -f "$GAME_DIR/lua52.dll" ]; then
    echo "Backing up original lua52.dll -> lua52_original.dll"
    cp "$GAME_DIR/lua52.dll" "$GAME_DIR/lua52_original.dll"
fi
cp "$SCRIPT_DIR/lua52.dll" "$GAME_DIR/lua52.dll"
echo "Installed: $GAME_DIR/lua52.dll"

# Wine registry setup for AppInit_DLLs (stdout_redirect)
if [ -n "$WINE_PREFIX" ]; then
    echo ""
    echo "=== Setting up Wine registry ==="
    # Convert Linux path to Wine Z: path
    WINE_DLL_PATH="Z:$(echo "$GAME_DIR/stdout_redirect.dll" | sed 's|/|\\\\|g')"
    cp "$SCRIPT_DIR/stdout_redirect.dll" "$GAME_DIR/stdout_redirect.dll"

    REG_FILE="$SCRIPT_DIR/appinit.reg"
    cat > "$REG_FILE" << REGEOF
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Windows]
"AppInit_DLLs"="$WINE_DLL_PATH"
"LoadAppInit_DLLs"=dword:00000001
REGEOF

    WINEPREFIX="$WINE_PREFIX" wine regedit "$REG_FILE" 2>/dev/null && echo "Registry updated." || {
        echo "Note: wine regedit unavailable, editing registry directly..."
        SYSTEM_REG="$WINE_PREFIX/system.reg"
        if [ -f "$SYSTEM_REG" ]; then
            if grep -q "AppInit_DLLs" "$SYSTEM_REG" 2>/dev/null; then
                sed -i "s|\"AppInit_DLLs\"=.*|\"AppInit_DLLs\"=\"$WINE_DLL_PATH\"|" "$SYSTEM_REG"
                sed -i 's|"LoadAppInit_DLLs"=.*|"LoadAppInit_DLLs"=dword:00000001|' "$SYSTEM_REG"
            fi
        fi
    }
else
    echo "[!] Wine prefix not found - skipping registry setup"
fi

echo ""
echo "=== Done ==="
echo "Launch Hades and check for hades_lua_stdout.log in $GAME_DIR"
echo "To uninstall: remove VERSION.dll, lua52.dll from $GAME_DIR,"
echo "  rename lua52_original.dll back to lua52.dll."
