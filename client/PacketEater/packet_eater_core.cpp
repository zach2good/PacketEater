#include "packet_eater_core.h"

#include "base64pp.h"
#include "json.hpp"

void PacketEaterCore::SendPutRequest(const std::string& path, const std::string& payload)
{
    if (!DetectRetail())
    {
        return;
    }

    // clang-format off
    m_TaskSystem.schedule([this, path, payload]()
    {
        // If multiple tasks are created they might all try to create/use the
        // http client, so wrap each task in a lock_guard and mutex.
        std::lock_guard<std::mutex> lg(m_CLIMutex);
        try
        {
            // Lazy load the http client
            if (m_CLI == nullptr)
            {
                m_CLI = std::make_unique<httplib::Client>(m_URL);
            }

            // TODO: gzip
            // TODO: Handle response codes
            // TODO: On a successful submission we'll get back a JSON response with code 202.
            //     : This will also have the submitter identifier and capture session identifier.
            //     : On the first successful submission we should log these to the user.
            std::ignore = m_CLI->Post(path, payload, "application/json");
        }
        catch (std::exception e)
        {
            // TODO: Error logging
        }
    });
    // clang-format on
}

bool PacketEaterCore::DetectRetail()
{
    return GetModuleHandleA("polhook.dll") != NULL;
}

void PacketEaterCore::HandlePacketData(CharacterInfo const& info, uint8_t* data, uint32_t dataSz, PacketDirection direction, OriginProgram origin)
{
    const auto now       = std::chrono::system_clock::now();
    const auto now_ms    = std::chrono::time_point_cast<std::chrono::milliseconds>(now);
    const auto timestamp = now_ms.time_since_epoch().count();

    // TODO: Censor sensitive data here (0x000D packets, etc)

    const auto payload = base64pp::encode({data, dataSz});

    using json = nlohmann::json;
    json j;

    // NOTE: These must be the same keys as the server expects
    j["name"]      = info.name;
    j["zone_id"]   = info.zone_id;
    j["version"]   = info.version;
    j["timestamp"] = timestamp;
    j["payload"]   = payload;
    j["direction"] = direction;
    j["origin"]    = origin;

    SendPutRequest("/upload", j.dump());
}
