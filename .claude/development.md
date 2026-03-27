# Development

## Commands
```bash
python3 build.py                                    # build + deploy DLLs
python3 build.py --no-deploy                        # build only
python3 build.py --clean
python3 deploy_mod.py                               # deploy Lua mods

python3 hadesmp_bridge.py --mode solo               # test without network
python3 hadesmp_bridge.py --mode host
python3 hadesmp_bridge.py --mode client --host <ip>

python3 -m pytest tests/ -v
```

## Dependencies
Python stdlib only: `socket`, `threading`, `json`, `struct`, `pathlib`, `dataclasses`, `subprocess`
C compilation: Linux/WSL2 → `x86_64-w64-mingw32-gcc`; Windows → GCC or `cl.exe`
