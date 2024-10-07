#pragma once

#define WIN32_LEAN_AND_MEAN
#include <WinSock2.h>
#include "httplib.h"
#include "task_system.h"

#include <string>
#include <memory>

template <typename T, typename U>
T& ref(U* buf, std::size_t index)
{
    return *reinterpret_cast<T*>(reinterpret_cast<uint8_t*>(buf) + index);
}

struct CharacterInfo
{
    std::string name;    // Used to remove the character name before we submit the data
    uint16_t    zone_id; //
    std::string version; // client version

    // TODO?: in-game time
    // TODO?: character pos
};

enum class PacketDirection : uint8_t
{
    S2C = 0,
    C2S = 1,
};

enum class OriginProgram : uint8_t
{
    Ashita_v3   = 0,
    Ashita_v4   = 1,
    Windower_v4 = 2,
    Windower_v5 = 3,
};

class PacketEaterCore
{
public:
    PacketEaterCore()  = default;
    ~PacketEaterCore() = default;

    PacketEaterCore(const PacketEaterCore& other)            = delete;
    PacketEaterCore(PacketEaterCore&& other)                 = delete;

    PacketEaterCore& operator=(PacketEaterCore&& other)      = delete;
    PacketEaterCore& operator=(const PacketEaterCore& other) = delete;

    void SendPutRequest(const std::string& path, const std::string& payload);
    bool DetectRetail();

    void HandlePacketData(CharacterInfo const& info, uint8_t* data, uint32_t dataSz, PacketDirection direction, OriginProgram origin);

private:
    ts::task_system m_TaskSystem;

    std::unique_ptr<httplib::Client> m_CLI;

    std::mutex m_CLIMutex;

    // TODO: Make configurable
    // Default value
    std::string m_URL = "http://localhost";
};
