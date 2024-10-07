import requests
import os
import random
import gzip
import io
import time
import requests
import concurrent.futures

url = "http://localhost/upload"


def send_packet():
    random_data = os.urandom(random.randint(256, 4096))
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as f:
        f.write(random_data)

    gzipped_data = buffer.getvalue()
    files = {"file": ("random_data.gz", gzipped_data, "application/gzip")}

    try:
        response = requests.post(url, files=files)
        if response.status_code == 202:
            print(f"Packet sent successfully: {response.json()}")
        else:
            print(f"Failed to send packet: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending packet: {e}")


if __name__ == "__main__":
    while True:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            executor.submit(send_packet)
            time.sleep(1.0)
