-- HadesMP.lua — Main mod entry point
-- Loaded via EXEC:dofile() from the Python bridge on first heartbeat.
--
-- Responsibilities:
--   - Heartbeat loop (~100ms, prints HADESMP:HB to stdout)
--   - Inbox polling (dofile hadesmp_inbox.lua, check seq, dispatch messages)
--   - P1 state reporting (position ~10Hz, room on transitions)
--   - Message dispatch to handler functions

local HadesMP = {}

HadesMP.Version = "0.1.0"
HadesMP.Initialized = false
HadesMP.LastInboxSeq = 0
HadesMP.HeartbeatInterval = 0.1  -- seconds
HadesMP.PositionReportInterval = 0.1  -- ~10Hz
HadesMP.LastPositionReport = 0
HadesMP.LastRoom = nil
HadesMP.P2Enabled = false
HadesMP.Debug = false

-- Store globally so bridge and other modules can access
_G.HadesMP = HadesMP

-- ============================================================
-- Inbox polling
-- ============================================================

function HadesMP.PollInbox()
    -- Find the inbox file relative to the game's working directory
    local path = "hadesmp_inbox.lua"
    local ok, result = pcall(dofile, path)
    if not ok then
        -- File doesn't exist or parse error — normal when bridge hasn't written yet
        return
    end
    if type(result) ~= "table" then
        return
    end
    if not result.seq or result.seq <= HadesMP.LastInboxSeq then
        return  -- Already processed this batch
    end

    HadesMP.LastInboxSeq = result.seq

    -- Acknowledge receipt
    print("HADESMP:ACK:" .. tostring(result.seq))

    -- Dispatch each message
    if result.msgs then
        for _, msg in ipairs(result.msgs) do
            HadesMP.DispatchMessage(msg)
        end
    end
end

-- ============================================================
-- Message dispatch
-- ============================================================

function HadesMP.DispatchMessage(msg)
    local colon = string.find(msg, ":", 1, true)
    local cmd, payload
    if colon then
        cmd = string.sub(msg, 1, colon - 1)
        payload = string.sub(msg, colon + 1)
    else
        cmd = msg
        payload = ""
    end

    if cmd == "PING" then
        print("HADESMP:PONG:" .. payload)

    elseif cmd == "NOP" then
        -- No-op, just ACK was enough

    elseif cmd == "MSG" then
        print("HADESMP:MSG:echo:" .. payload)

    elseif cmd == "EXEC" then
        HadesMP.ExecLua(payload)

    elseif cmd == "P2ENABLE" then
        HadesMP.HandleP2Enable(payload)

    elseif cmd == "P2POS" then
        HadesMP.HandleP2Pos(payload)

    elseif cmd == "P2MOVE" then
        HadesMP.HandleP2Move(payload)

    elseif cmd == "P2FACE" then
        HadesMP.HandleP2Face(payload)

    elseif cmd == "P2FIRE" then
        HadesMP.HandleP2Fire(payload)

    elseif cmd == "P2ANIM" then
        HadesMP.HandleP2Anim(payload)

    elseif cmd == "P2SYNC" then
        HadesMP.HandleP2Sync(payload)

    else
        if HadesMP.Debug then
            print("HADESMP:MSG:unknown_cmd=" .. cmd)
        end
    end
end

-- ============================================================
-- EXEC handler
-- ============================================================

function HadesMP.ExecLua(code)
    local fn, err = load(code)
    if not fn then
        print("HADESMP:EXEC_ERR:" .. tostring(err))
        return
    end
    local ok, result = pcall(fn)
    if ok then
        print("HADESMP:EXEC_OK:" .. tostring(result or "nil"))
    else
        print("HADESMP:EXEC_ERR:" .. tostring(result))
    end
end

-- ============================================================
-- P2 command handlers (delegate to HadesMPP2 if loaded)
-- ============================================================

function HadesMP.HandleP2Enable(payload)
    if not _G.HadesMPP2 then
        -- Try to load P2 module
        local ok, err = pcall(function()
            dofile("Content/Mods/HadesMP/HadesMPP2.lua")
        end)
        if not ok then
            print("HADESMP:P2EVT:err=failed_to_load_P2_module:" .. tostring(err))
            return
        end
    end

    if payload == "1" then
        HadesMP.P2Enabled = true
        print("HADESMP:P2EVT:enabled")
        if _G.HadesMPP2 then
            _G.HadesMPP2.Enable()
        end
    else
        HadesMP.P2Enabled = false
        if _G.HadesMPP2 then
            _G.HadesMPP2.Disable()
        end
        print("HADESMP:P2EVT:disabled")
    end
end

function HadesMP.HandleP2Pos(payload)
    if _G.HadesMPP2 then
        local x, y = string.match(payload, "([%d%.%-]+),([%d%.%-]+)")
        if x and y then
            _G.HadesMPP2.SetPosition(tonumber(x), tonumber(y))
        end
    else
        print("HADESMP:P2EVT:err=P2_not_loaded")
    end
end

function HadesMP.HandleP2Move(payload)
    if _G.HadesMPP2 then
        local dx, dy = string.match(payload, "([%d%.%-]+),([%d%.%-]+)")
        if dx and dy then
            _G.HadesMPP2.Move(tonumber(dx), tonumber(dy))
        end
    else
        print("HADESMP:P2EVT:err=P2_not_loaded")
    end
end

function HadesMP.HandleP2Face(payload)
    if _G.HadesMPP2 then
        local angle = tonumber(payload)
        if angle then
            _G.HadesMPP2.SetFacing(angle)
        end
    else
        print("HADESMP:P2EVT:err=P2_not_loaded")
    end
end

function HadesMP.HandleP2Fire(payload)
    if _G.HadesMPP2 then
        _G.HadesMPP2.FireWeapon(payload)
    else
        print("HADESMP:P2EVT:err=P2_not_loaded")
    end
end

function HadesMP.HandleP2Anim(payload)
    if _G.HadesMPP2 then
        _G.HadesMPP2.SetAnimation(payload)
    else
        print("HADESMP:P2EVT:err=P2_not_loaded")
    end
end

function HadesMP.HandleP2Sync(payload)
    if _G.HadesMPP2 then
        local x, y, angle, anim = string.match(payload, "([%d%.%-]+),([%d%.%-]+),([%d%.%-]+),(.*)")
        if x and y and angle then
            _G.HadesMPP2.Sync(tonumber(x), tonumber(y), tonumber(angle), anim or "")
        end
    else
        print("HADESMP:P2EVT:err=P2_not_loaded")
    end
end

-- ============================================================
-- State reporting
-- ============================================================

function HadesMP.ReportPosition()
    local now = _G.GetTime and GetTime() or os.clock()
    if now - HadesMP.LastPositionReport < HadesMP.PositionReportInterval then
        return
    end
    HadesMP.LastPositionReport = now

    if not CurrentRun or not CurrentRun.Hero then
        return
    end

    local heroId = CurrentRun.Hero.ObjectId
    if not heroId then
        return
    end

    local ok, loc = pcall(GetLocation, { Id = heroId })
    if not ok or not loc then
        return
    end

    local angle = 0
    local ok2, a = pcall(GetAngle, { Id = heroId })
    if ok2 and a then
        angle = a
    end

    print(string.format("HADESMP:P1POS:%.1f,%.1f,%.2f", loc.X, loc.Y, angle))
end

function HadesMP.ReportRoom()
    if not CurrentRun or not CurrentRun.CurrentRoom then
        return
    end

    local roomName = CurrentRun.CurrentRoom.Name or "unknown"
    if roomName ~= HadesMP.LastRoom then
        HadesMP.LastRoom = roomName
        print("HADESMP:ROOM:" .. roomName)

        -- Notify P2 module of room change
        if HadesMP.P2Enabled and _G.HadesMPP2 then
            _G.HadesMPP2.OnRoomChange(roomName)
        end
    end
end

-- ============================================================
-- Main heartbeat loop (runs as a coroutine via thread)
-- ============================================================

function HadesMP.HeartbeatLoop()
    while true do
        -- Heartbeat signal
        print("HADESMP:HB")

        -- Poll inbox for messages from bridge
        local ok, err = pcall(HadesMP.PollInbox)
        if not ok and HadesMP.Debug then
            print("HADESMP:MSG:inbox_err=" .. tostring(err))
        end

        -- Report state
        local ok2, err2 = pcall(HadesMP.ReportPosition)
        if not ok2 and HadesMP.Debug then
            print("HADESMP:MSG:pos_err=" .. tostring(err2))
        end

        local ok3, err3 = pcall(HadesMP.ReportRoom)
        if not ok3 and HadesMP.Debug then
            print("HADESMP:MSG:room_err=" .. tostring(err3))
        end

        -- Wait for next tick
        wait(HadesMP.HeartbeatInterval)
    end
end

-- ============================================================
-- Initialization
-- ============================================================

function HadesMP.Init()
    if HadesMP.Initialized then
        print("HADESMP:MSG:already_initialized")
        return
    end
    HadesMP.Initialized = true

    print("HADESMP:INIT:" .. HadesMP.Version)

    -- Start heartbeat loop as a game thread
    -- Hades uses a coroutine-based threading model via thread()
    if _G.thread then
        thread(HadesMP.HeartbeatLoop)
    else
        -- Fallback: if thread() isn't available, use a OnUpdate hook approach
        -- This shouldn't happen in normal Hades runtime
        print("HADESMP:MSG:warn=thread_not_available,using_manual_loop")
    end

    print("HADESMP:READY")
end

-- Auto-initialize when loaded
HadesMP.Init()

return HadesMP
