from database import PacketDirection

packet_lookup = {
    PacketDirection.C2S: {},
    PacketDirection.S2C: {
        0xDF: "Char Health",
    },
}
