# Sync Service Configuration Examples

## PostgreSQL Configuration

### Using Connection String

```python
# In app/services/postgres_service.py
from app.services.postgres_service import PostgresService

# Default (uses hardcoded connection)
pg_service = PostgresService()

# Custom connection string
pg_service = PostgresService(
    connection_string="postgresql://user:password@localhost:5432/hala-app?schema=public"
)

await pg_service.connect()
```

### Using Environment Variables

```bash
# In .env file
DATABASE_URL=postgresql://wildanmaulana@localhost:5432/hala-app?schema=public
POSTGRES_USER=wildanmaulana
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=hala-app
```

## ChromaDB Configuration

### Default (Persistent Local)

```python
from app.services.chromadb_service import ChromaDBService

# Uses ./chromadb_data directory
chroma_service = ChromaDBService()
await chroma_service.connect()
```

### Custom Directory

```python
chroma_service = ChromaDBService(
    persist_directory="/var/chromadb_data"
)
await chroma_service.connect()
```

## Sync Service Configuration

### Full Sync (Development/Testing)

```python
from app.services.sync_service import SyncService

sync_service = SyncService()

# Clears all ChromaDB data and rebuilds
stats = await sync_service.sync_all(force_full_sync=True)
```

### Incremental Sync (Production)

```python
sync_service = SyncService()

# Only syncs new/updated records
stats = await sync_service.sync_all(force_full_sync=False)
```

## REST API Examples

### JavaScript/Fetch

```javascript
// Full sync
async function runFullSync() {
  const response = await fetch("http://localhost:8000/api/v1/sync/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force_full_sync: true }),
  });
  return await response.json();
}

// Incremental sync
async function runIncrementalSync() {
  const response = await fetch("http://localhost:8000/api/v1/sync/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force_full_sync: false }),
  });
  return await response.json();
}

// Get stats
async function getStats() {
  const response = await fetch("http://localhost:8000/api/v1/sync/stats");
  return await response.json();
}
```

### Python/Requests

```python
import requests
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

# Full sync
response = requests.post(
    f"{BASE_URL}/sync/run",
    json={"force_full_sync": True}
)
print(response.json())

# Incremental sync
response = requests.post(
    f"{BASE_URL}/sync/run",
    json={"force_full_sync": False}
)
print(response.json())

# Get stats
response = requests.get(f"{BASE_URL}/sync/stats")
print(response.json())
```

### cURL

```bash
# Full sync
curl -X POST http://localhost:8000/api/v1/sync/run \
  -H "Content-Type: application/json" \
  -d '{"force_full_sync": true}'

# Incremental sync
curl -X POST http://localhost:8000/api/v1/sync/run \
  -H "Content-Type: application/json" \
  -d '{"force_full_sync": false}'

# Get stats
curl http://localhost:8000/api/v1/sync/stats

# Sync single knowledge reference
curl -X POST http://localhost:8000/api/v1/sync/knowledge-reference/{id}

# Sync single journey template
curl -X POST http://localhost:8000/api/v1/sync/journey-template/{id}

# Health check
curl http://localhost:8000/api/v1/sync/health
```

## CLI Examples

### Basic Commands

```bash
# Full synchronization
python -m app.cli.sync full

# Incremental synchronization
python -m app.cli.sync incremental

# Show statistics
python -m app.cli.sync stats

# Sync single knowledge reference
python -m app.cli.sync ref c_123abc

# Sync single journey template
python -m app.cli.sync template t_456def
```

### Cronjob Configuration

#### Linux/macOS Crontab

**Every 6 hours:**

```cron
0 */6 * * * /home/user/hala-app/venv/bin/python -m app.cli.sync incremental >> /var/log/hala-sync.log 2>&1
```

**Every day at 2 AM:**

```cron
0 2 * * * /home/user/hala-app/venv/bin/python -m app.cli.sync full >> /var/log/hala-sync.log 2>&1
```

**Every week on Sunday at 3 AM:**

```cron
0 3 * * 0 /home/user/hala-app/venv/bin/python -m app.cli.sync full >> /var/log/hala-sync.log 2>&1
```

#### Systemd Timer (Alternative)

Create `/etc/systemd/system/hala-sync.service`:

```ini
[Unit]
Description=Hala AI Data Sync Service
After=network.target

[Service]
Type=oneshot
User=hala
WorkingDirectory=/home/hala/hala-app
ExecStart=/home/hala/hala-app/venv/bin/python -m app.cli.sync incremental
StandardOutput=append:/var/log/hala-sync.log
StandardError=append:/var/log/hala-sync.log

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/hala-sync.timer`:

```ini
[Unit]
Description=Run Hala AI Data Sync every 6 hours

[Timer]
OnBootSec=10min
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable hala-sync.timer
sudo systemctl start hala-sync.timer
sudo systemctl status hala-sync.timer
```

## Logging Configuration

### Console + File Logging

```python
import logging

# In your application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('./sync.log')
    ]
)

logger = logging.getLogger(__name__)
logger.info("Sync started")
```

### Rotating File Handler

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    './sync.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
logging.root.addHandler(handler)
```

## Docker Composition

### docker-compose.yml (with PostgreSQL and Sync)

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: wildanmaulana
      POSTGRES_DB: hala-app
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  hala-ai:
    build: .
    environment:
      DATABASE_URL: postgresql://wildanmaulana:password@postgres:5432/hala-app
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    volumes:
      - ./chromadb_data:/app/chromadb_data

  sync-scheduler:
    build: .
    command: /bin/bash -c "while true; do python -m app.cli.sync incremental; sleep 21600; done"
    environment:
      DATABASE_URL: postgresql://wildanmaulana:password@postgres:5432/hala-app
    depends_on:
      - postgres
    volumes:
      - ./chromadb_data:/app/chromadb_data

volumes:
  postgres_data:
```

## Error Handling Examples

### Try-Catch Pattern

```python
from app.services.sync_service import SyncService
import logging

logger = logging.getLogger(__name__)

async def safe_sync():
    sync_service = SyncService()

    try:
        stats = await sync_service.sync_all(force_full_sync=False)

        if stats['errors'] > 0:
            logger.warning(f"Sync completed with {stats['errors']} errors")

        logger.info(f"Synced {stats['knowledge_references_synced']} references and "
                   f"{stats['journey_templates_synced']} templates")

        return stats

    except ConnectionError as e:
        logger.error(f"Database connection failed: {e}")
        # Notify admin, retry later

    except Exception as e:
        logger.error(f"Unexpected error during sync: {e}")
        # Alert monitoring system
```

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def sync_with_retry():
    sync_service = SyncService()
    stats = await sync_service.sync_all()
    return stats

# Usage
try:
    stats = await sync_with_retry()
except Exception as e:
    print(f"Sync failed after retries: {e}")
```

## Monitoring and Alerts

### Health Check Endpoint

```bash
#!/bin/bash

# Check sync health every minute
while true; do
  response=$(curl -s http://localhost:8000/api/v1/sync/health)
  status=$(echo $response | jq -r '.status')

  if [ "$status" != "healthy" ]; then
    # Send alert
    echo "Sync service unhealthy!" | mail -s "Alert" admin@example.com
  fi

  sleep 60
done
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

sync_count = Counter('hala_sync_total', 'Total syncs', ['type'])
sync_duration = Histogram('hala_sync_duration_seconds', 'Sync duration')
sync_errors = Counter('hala_sync_errors_total', 'Sync errors')

@sync_duration.time()
async def monitored_sync():
    sync_service = SyncService()
    stats = await sync_service.sync_all()

    sync_count.labels(type='incremental').inc()
    sync_errors.inc(stats['errors'])

    return stats
```
