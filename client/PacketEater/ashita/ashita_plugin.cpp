/**
 * PacketEater by zach2good, based upon:
 *
 * Ashita Example Plugin - Copyright (c) Ashita Development Team
 * Contact: https://www.ashitaxi.com/
 * Contact: https://discord.gg/Ashita
 *
 * This file is part of Ashita Example Plugin.
 *
 * Ashita Example Plugin is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Ashita Example Plugin is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with Ashita Example Plugin.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "ashita_plugin.h"

#pragma comment(lib, "psapi.lib")
#include <psapi.h>

#include <filesystem>

PacketEater::PacketEater(void)
    : m_AshitaCore{nullptr}
    , m_LogManager{nullptr}
    , m_PluginId(0)
{
}

PacketEater::~PacketEater(void)
{
}

const char* PacketEater::GetName(void) const
{
    return "PacketEater";
}

const char* PacketEater::GetAuthor(void) const
{
    return "zach2good";
}

const char* PacketEater::GetDescription(void) const
{
    return "";
}

const char* PacketEater::GetLink(void) const
{
    return "";
}

double PacketEater::GetVersion(void) const
{
    return 1.1f;
}

double PacketEater::GetInterfaceVersion(void) const
{
    return ASHITA_INTERFACE_VERSION;
}

int32_t PacketEater::GetPriority(void) const
{
    return 0;
}

uint32_t PacketEater::GetFlags(void) const
{
    return (uint32_t)Ashita::PluginFlags::UsePackets;
}

bool PacketEater::Initialize(IAshitaCore* core, ILogManager* logger, const uint32_t id)
{
    this->m_AshitaCore = core;
    this->m_LogManager = logger;
    this->m_PluginId   = id;

    this->wrCore = std::make_unique<PacketEaterCore>();

    return true;
}

void PacketEater::Release(void)
{
    this->wrCore = nullptr;
}

auto PacketEater::getVersionStr() -> std::string
{
    // (Thanks Thorny!)

    std::string installPath = "";

    // Obtain the game module name configuration value in case of using an override..
    auto moduleName = m_AshitaCore->GetConfigurationManager()->GetString("boot", "ashita.boot", "gamemodule");
    if (moduleName == nullptr)
    {
        moduleName = "FFXiMain.dll";
    }
    else if (_stricmp(moduleName, "ffximain.dll"))
    {
        // Probably using a bootloader so private server check here..
        // TODO: Test this
        return "Unknown";
    }

    // Obtain the path to the game..
    const auto handle = ::GetModuleHandleA(moduleName);
    if (handle == nullptr)
    {
        // Could not find module..
        return "Unknown";
    }
    else
    {
        char buffer[4096];
        ::GetModuleFileNameA(handle, buffer, 4096);
        installPath = std::filesystem::canonical(std::filesystem::path(buffer).remove_filename()).string();
    }

    const auto filePath = installPath + std::string("/patch.cfg");

    std::ifstream patchCfg(filePath);
    if (!patchCfg.is_open())
    {
        return "Unknown";
    }

    std::string line;
    for (int i = 0; i < 2; i++) // Only read 2 lines
    {
        std::getline(patchCfg, line);
    }
    patchCfg.close();

    // Split on first space
    const auto pos = line.find(' ');
    if (pos == std::string::npos)
    {
        return "Unknown";
    }

    return line.substr(0, pos);
}

bool PacketEater::HandleIncomingPacket(uint16_t id, uint32_t size, const uint8_t* data, uint8_t* modified, uint32_t sizeChunk, const uint8_t* dataChunk, bool injected, bool blocked)
{
    CharacterInfo info;
    info.name    = m_AshitaCore->GetMemoryManager()->GetParty()->GetMemberName(0);
    info.zoneId  = m_AshitaCore->GetMemoryManager()->GetParty()->GetMemberZone(0);
    info.version = getVersionStr();
    this->wrCore->HandlePacketData(info, modified, size, PacketDirection::S2C, OriginProgram::Ashita_v4);
    return false;
}

bool PacketEater::HandleOutgoingPacket(uint16_t id, uint32_t size, const uint8_t* data, uint8_t* modified, uint32_t sizeChunk, const uint8_t* dataChunk, bool injected, bool blocked)
{
    CharacterInfo info;
    info.name    = m_AshitaCore->GetMemoryManager()->GetParty()->GetMemberName(0);
    info.zoneId  = m_AshitaCore->GetMemoryManager()->GetParty()->GetMemberZone(0);
    info.version = getVersionStr();
    this->wrCore->HandlePacketData(info, modified, size, PacketDirection::C2S, OriginProgram::Ashita_v4);
    return false;
}

extern "C" __declspec(dllexport) IPlugin* __stdcall expCreatePlugin(const char* args)
{
    UNREFERENCED_PARAMETER(args);
    return new PacketEater();
}

extern "C" __declspec(dllexport) double __stdcall expGetInterfaceVersion(void)
{
    return ASHITA_INTERFACE_VERSION;
}
