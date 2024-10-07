_addon.name = 'PacketEater'
_addon.author = 'zach2good, Heals'
_addon.version = '1.1'
_addon.command = 'PacketEater'

-- package.cpath somehow doesn't appreciate backslashes
local addon_path = windower.addon_path:gsub('\\', '/')
package.cpath = package.cpath .. ';' .. addon_path .. '/lib/?.dll'
require('_PacketEater')

local getVersionString = function()
    local path = string.format("%s/%s", windower.pol_path, "../FINAL FANTASY XI/patch.cfg")
    if not windower.file_exists(path) then
        print("File not found")
        return nil
    end

    local file = io.open(path, "r")
    if not file then
        print("Failed to open file")
        return nil
    end

    local _    = file:read("*l") -- Read the first line
    local line = file:read("*l") -- Read the second line
    file:close()

    function splitStr(s, sep)
        local fields = {}
        local pattern = string.format('([^%s]+)', sep)
        local _ = string.gsub(s, pattern, function(c)
            fields[#fields + 1] = c
        end)

        return fields
    end

    local version = splitStr(line, " ")[1]

    return version
end

local versionString = getVersionString()

windower.register_event('incoming chunk', function(id, data)
    local info          = windower.ffxi.get_info()
    local player_info   = windower.ffxi.get_player()
    player_info.zone_id = info.zone
    player_info.version = versionString
    _PacketEater.submit(player_info, data, "s2c")
end)

windower.register_event('outgoing chunk', function(id, data)
    local info          = windower.ffxi.get_info()
    local player_info   = windower.ffxi.get_player()
    player_info.zone_id = info.zone
    player_info.version = versionString
    _PacketEater.submit(player_info, data, "c2s")
end)
