import enum

#
# Enums
#


class PacketDirection(int, enum.Enum):
    S2C = 0
    C2S = 1

    @staticmethod
    def from_str(label):
        if label.upper() in ("S2C", "SERVER_TO_CLIENT"):
            return PacketDirection.S2C
        elif label.upper() in ("C2S", "CLIENT_TO_SERVER"):
            return PacketDirection.C2S
        else:
            raise NotImplementedError


#
# Lookups
#

packet_lookup = {
    PacketDirection.C2S: {},
    PacketDirection.S2C: {
        0xDF: "Char Health",
    },
}


#
# Helpers
#


def get_packet_type_and_size(data: bytes) -> tuple[int, int]:
    return data[0] & 0xFF | data[1] & 0x01, data[1] & 0xFE
