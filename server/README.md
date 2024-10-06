# FFXI Packet Eater Server

_Built using https://github.com/testdrivenio/fastapi-celery_

### Building/Running

```sh
cp .env.example .env
docker-compose up --build
```

#### Test Client

```sh
# Send random data to the /submit endpoint
python3 send_packets.py
```
