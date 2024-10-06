import hashlib


def generate_identifier(ip_address: str) -> str:
    sha = hashlib.sha256()
    sha.update(ip_address.encode("utf-8"))
    return sha.hexdigest()


def human_readable_size_str(packets_bytes: int) -> str:
    if packets_bytes == 0 or packets_bytes == None:
        return f"0 B"
    elif packets_bytes < 1024:
        return f"{packets_bytes} B"
    elif packets_bytes < 1024**2:
        return f"{packets_bytes / 1024:.2f} KB"
    elif packets_bytes < 1024**3:
        return f"{packets_bytes / 1024 ** 2:.2f} MB"
    else:
        return f"{packets_bytes / 1024 ** 3:.2f} GB"
