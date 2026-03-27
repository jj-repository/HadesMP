# Networking & Protocol

## Transport
- TCP: reliable — `[4B length][1B type][JSON]`
- UDP: position — `[2B seq][1B type][JSON]`, 20Hz, drops stale

## Lua → Python (stdout log)
```
HADESMP:HB                        # Heartbeat ~10Hz
HADESMP:P1POS:<x>,<y>,<angle>
HADESMP:ROOM:<name>
HADESMP:ACK:<seq>
HADESMP:PONG:<timestamp>
HADESMP:P2EVT:<payload>
```

## Python → Lua (inbox file)
```
PING:<timestamp>
P2ENABLE:<0|1>
P2SYNC:<x>,<y>,<angle>,<anim>
EXEC:<lua_code>
```

## Security
- Atomic inbox writes via temp + `os.replace()`
- UDP sequence numbering (drops stale)
- Thread-safe shared state with locks
- No shell=True in subprocess calls
- No encryption — LAN/friend use only (accepted)
