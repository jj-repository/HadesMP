-- HadesMPP2.lua — Player 2 Entity Manager
-- Manages spawning, positioning, and control of the P2 entity in Hades.
--
-- P2 is spawned as a TrainingMeleeSummon (Skelly) with invulnerability.
-- Receives commands from the Python bridge via HadesMP message dispatch.

local HadesMPP2 = {}

HadesMPP2.Enabled = false
HadesMPP2.ObjectId = nil
HadesMPP2.EntityData = nil
HadesMPP2.SpawnOffset = { X = 200, Y = 0 }
HadesMPP2.EntityName = "TrainingMeleeSummon"

-- Store globally
_G.HadesMPP2 = HadesMPP2

-- ============================================================
-- Spawning
-- ============================================================

function HadesMPP2.Spawn()
    if HadesMPP2.ObjectId then
        -- Already spawned
        return true
    end

    if not CurrentRun or not CurrentRun.Hero then
        print("HADESMP:P2EVT:err=no_hero_for_spawn")
        return false
    end

    local ed = EnemyData[HadesMPP2.EntityName]
    if not ed then
        print("HADESMP:P2EVT:err=no_EnemyData_for_" .. HadesMPP2.EntityName)
        return false
    end

    local e = DeepCopyTable(ed)
    local ok, id = pcall(SpawnUnit, {
        Name = ed.Name,
        Group = "Standing",
        DestinationId = CurrentRun.Hero.ObjectId,
        OffsetX = HadesMPP2.SpawnOffset.X,
        OffsetY = HadesMPP2.SpawnOffset.Y,
    })

    if not ok or not id or id == 0 then
        print("HADESMP:P2EVT:err=spawn_failed:" .. tostring(id))
        return false
    end

    e.ObjectId = id

    -- Set up the entity
    local ok2, err2 = pcall(SetupEnemyObject, e, CurrentRun)
    if not ok2 then
        print("HADESMP:P2EVT:err=setup_failed:" .. tostring(err2))
    end

    -- Make invulnerable
    pcall(SetInvulnerable, { Id = id })

    HadesMPP2.ObjectId = id
    HadesMPP2.EntityData = e
    _G.P2 = e  -- Legacy global for test scripts

    print("HADESMP:P2EVT:spawned=" .. tostring(id))
    return true
end

function HadesMPP2.Despawn()
    if not HadesMPP2.ObjectId then
        return
    end

    local id = HadesMPP2.ObjectId
    pcall(Destroy, { Id = id })

    HadesMPP2.ObjectId = nil
    HadesMPP2.EntityData = nil
    _G.P2 = nil

    print("HADESMP:P2EVT:despawned")
end

-- ============================================================
-- Enable / Disable
-- ============================================================

function HadesMPP2.Enable()
    HadesMPP2.Enabled = true
    HadesMPP2.Spawn()
end

function HadesMPP2.Disable()
    HadesMPP2.Enabled = false
    HadesMPP2.Despawn()
end

-- ============================================================
-- Movement and positioning
-- ============================================================

function HadesMPP2.SetPosition(x, y)
    if not HadesMPP2.ObjectId then
        print("HADESMP:P2EVT:err=no_P2_for_pos")
        return
    end

    local ok, err = pcall(Teleport, {
        Id = HadesMPP2.ObjectId,
        OffsetX = x,
        OffsetY = y,
    })
    if not ok then
        print("HADESMP:P2EVT:err=teleport:" .. tostring(err))
    end
end

function HadesMPP2.Move(dx, dy)
    if not HadesMPP2.ObjectId then
        return
    end

    -- Get current position, apply delta, teleport
    local ok, loc = pcall(GetLocation, { Id = HadesMPP2.ObjectId })
    if not ok or not loc then
        return
    end

    pcall(Teleport, {
        Id = HadesMPP2.ObjectId,
        OffsetX = loc.X + dx,
        OffsetY = loc.Y + dy,
    })
end

function HadesMPP2.SetFacing(angle)
    if not HadesMPP2.ObjectId then
        return
    end

    -- Hades uses SetAngle or AngleTowardTarget
    pcall(SetAngle, { Id = HadesMPP2.ObjectId, Angle = angle })
end

-- ============================================================
-- Combat
-- ============================================================

function HadesMPP2.FireWeapon(weaponName)
    if not HadesMPP2.ObjectId then
        print("HADESMP:P2EVT:err=no_P2_for_fire")
        return
    end

    weaponName = weaponName or "SwordWeapon"

    pcall(FireWeaponFromUnit, {
        Id = HadesMPP2.ObjectId,
        Weapon = weaponName,
        AutoEquip = true,
    })
end

-- ============================================================
-- Animation
-- ============================================================

function HadesMPP2.SetAnimation(animName)
    if not HadesMPP2.ObjectId then
        return
    end

    pcall(SetAnimation, {
        DestinationId = HadesMPP2.ObjectId,
        Name = animName,
    })
end

-- ============================================================
-- Combined sync (position + facing + animation in one call)
-- ============================================================

function HadesMPP2.Sync(x, y, angle, anim)
    if not HadesMPP2.ObjectId then
        return
    end

    -- Position
    pcall(Teleport, {
        Id = HadesMPP2.ObjectId,
        OffsetX = x,
        OffsetY = y,
    })

    -- Facing
    if angle then
        pcall(SetAngle, { Id = HadesMPP2.ObjectId, Angle = angle })
    end

    -- Animation (if specified)
    if anim and anim ~= "" then
        pcall(SetAnimation, {
            DestinationId = HadesMPP2.ObjectId,
            Name = anim,
        })
    end
end

-- ============================================================
-- Room lifecycle
-- ============================================================

function HadesMPP2.OnRoomChange(roomName)
    -- Despawn P2 on room transition (entity IDs are invalidated)
    if HadesMPP2.ObjectId then
        HadesMPP2.ObjectId = nil
        HadesMPP2.EntityData = nil
        _G.P2 = nil
        print("HADESMP:P2EVT:despawned")
    end

    -- Re-spawn if enabled (slight delay to let room load)
    if HadesMPP2.Enabled then
        -- Use a thread to add a small delay for room initialization
        if _G.thread then
            thread(function()
                wait(0.5)
                if HadesMPP2.Enabled then
                    HadesMPP2.Spawn()
                end
            end)
        else
            HadesMPP2.Spawn()
        end
    end
end

-- ============================================================
-- Utility
-- ============================================================

function HadesMPP2.GetPosition()
    if not HadesMPP2.ObjectId then
        return nil
    end

    local ok, loc = pcall(GetLocation, { Id = HadesMPP2.ObjectId })
    if ok and loc then
        return { X = loc.X, Y = loc.Y }
    end
    return nil
end

return HadesMPP2
