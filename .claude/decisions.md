# Decisions & Known Issues

## Design Decisions
| Decision | Rationale |
|----------|-----------|
| DLL proxy (not StyxScribe) | Works without ModImporter dependency |
| File-based IPC (not pipes) | More reliable across Wine/Proton boundary |
| Dual-instance architecture | Each player controls local hero, zero input lag |
| Python bridge | Fast iteration; IPC/networking don't need native speed |
| UDP for positions | 20Hz can tolerate packet loss |

## Won't Fix
| Issue | Reason |
|-------|--------|
| No macOS | Hades on macOS doesn't support mods |
| File IPC latency (~50ms) | Acceptable; positions use UDP directly |
| No network encryption | LAN/friend use only |

## Known Issues
1. No requirements.txt (stdlib only, build deps unlisted)
2. No CI/CD
3. P2 uses TrainingMeleeSummon placeholder (not a proper hero)
4. StyxScribe throughput unvalidated on Proton

## Focus
Do NOT optimize infrastructure. Focus on gameplay integration (Phases 1-2). Bridge and networking layers are solid.

## Review (2026-03-18 — WIP)
Platform detection tested, networking tested, atomic file I/O, thread-safe state, daemon threads with shutdown ✓
