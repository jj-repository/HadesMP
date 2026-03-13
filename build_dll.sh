#!/bin/bash
# Build and install the stdout redirect DLL for Hades/Wine
set -e

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
HADES_ROOT="/mnt/ext4gamedrive/SteamLibrary/steamapps/common/Hades"
WINE_PREFIX="/mnt/ext4gamedrive/SteamLibrary/steamapps/compatdata/1145360/pfx"

echo "=== Building stdout_redirect.dll ==="
x86_64-w64-mingw32-gcc -shared -o "$SCRIPT_DIR/stdout_redirect.dll" \
    "$SCRIPT_DIR/stdout_redirect.c" \
    -Wl,--subsystem,windows \
    -O2

echo "Built: $SCRIPT_DIR/stdout_redirect.dll"
ls -la "$SCRIPT_DIR/stdout_redirect.dll"

echo ""
echo "=== Installing to Wine prefix ==="

# Copy DLL to the game's directory (Wine can find it there)
DLL_DEST="$HADES_ROOT/x64Vk/stdout_redirect.dll"
cp "$SCRIPT_DIR/stdout_redirect.dll" "$DLL_DEST"
echo "Copied to: $DLL_DEST"

# Register as AppInit_DLL in Wine registry
# AppInit_DLLs loads the DLL into every process that loads user32.dll
REG_FILE="$SCRIPT_DIR/appinit.reg"
cat > "$REG_FILE" << 'REGEOF'
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\Windows]
"AppInit_DLLs"="Z:\\mnt\\ext4gamedrive\\SteamLibrary\\steamapps\\common\\Hades\\x64Vk\\stdout_redirect.dll"
"LoadAppInit_DLLs"=dword:00000001
REGEOF

echo "Importing registry key..."
WINEPREFIX="$WINE_PREFIX" wine regedit "$REG_FILE" 2>/dev/null || {
    echo "Note: wine regedit not directly available. Manually editing registry..."
    # Direct registry file edit as fallback
    SYSTEM_REG="$WINE_PREFIX/system.reg"
    if [ -f "$SYSTEM_REG" ]; then
        # Check if the key already exists
        if grep -q "AppInit_DLLs" "$SYSTEM_REG" 2>/dev/null; then
            echo "AppInit_DLLs key already exists in registry, updating..."
            sed -i 's|"AppInit_DLLs"=.*|"AppInit_DLLs"="Z:\\\\mnt\\\\ext4gamedrive\\\\SteamLibrary\\\\steamapps\\\\common\\\\Hades\\\\x64Vk\\\\stdout_redirect.dll"|' "$SYSTEM_REG"
            sed -i 's|"LoadAppInit_DLLs"=.*|"LoadAppInit_DLLs"=dword:00000001|' "$SYSTEM_REG"
        else
            echo "Adding AppInit_DLLs key to registry..."
            # Find the Windows NT\CurrentVersion\Windows section and add the values
            # If the section doesn't exist, we'll need to add it
            if grep -q '\[Software\\\\Microsoft\\\\Windows NT\\\\CurrentVersion\\\\Windows\]' "$SYSTEM_REG"; then
                sed -i '/\[Software\\\\Microsoft\\\\Windows NT\\\\CurrentVersion\\\\Windows\]/a "AppInit_DLLs"="Z:\\\\mnt\\\\ext4gamedrive\\\\SteamLibrary\\\\steamapps\\\\common\\\\Hades\\\\x64Vk\\\\stdout_redirect.dll"\n"LoadAppInit_DLLs"=dword:00000001' "$SYSTEM_REG"
            else
                echo "Registry section not found - will need manual registry edit"
                echo "Run this in the game's Wine prefix:"
                echo "  WINEPREFIX=$WINE_PREFIX wine regedit $REG_FILE"
            fi
        fi
    fi
}

echo ""
echo "=== Creating stdout log file ==="
touch /tmp/hades_lua_stdout.log
echo "Log file: /tmp/hades_lua_stdout.log"

echo ""
echo "=== Done ==="
echo "To test: launch Hades, then: tail -f /tmp/hades_lua_stdout.log"
echo "To uninstall: delete $DLL_DEST and remove AppInit_DLLs from registry"
