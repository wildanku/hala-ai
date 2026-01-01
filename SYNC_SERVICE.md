# Data Sync Service Documentation

## Overview

The Sync Service synchronizes data between PostgreSQL and ChromaDB vector database. It handles two main data types:

1. **KnowledgeReference** - Islamic knowledge sources (verses, hadith, strategies, dua)
2. **JourneyTemplate** - User journey templates with goals and tags

## Architecture

```
PostgreSQL → PostgreSQL Service → Sync Service → ChromaDB Service → ChromaDB
    ↓              (asyncpg)          ↓            (chromadb)         ↓
KnowledgeReference                  Document                    Vector Store
JourneyTemplate                     Preparation
```

## Components

### 1. PostgreSQL Service (`app/services/postgres_service.py`)

Handles connections and queries to PostgreSQL database.

**Features:**

- Connection pooling with asyncpg
- Support for fetching all records or specific records
- Timestamp-based incremental updates
- Automatic JSON parsing for localized content

**Usage:**

```python
postgres_service = PostgresService()
await postgres_service.connect()

# Fetch all knowledge references
references = await postgres_service.fetch_knowledge_references()

# Fetch specific knowledge reference
reference = await postgres_service.fetch_knowledge_reference("ref_id")

# Incremental sync
updated_refs = await postgres_service.get_knowledge_references_updated_since("2024-01-01")

await postgres_service.disconnect()
```

### 2. ChromaDB Service (`app/services/chromadb_service.py`)

Manages vector database operations.

**Features:**

- Persistent client with local file storage
- Separate collections for knowledge references and templates
- Semantic search capabilities
- Metadata filtering (category, tags, status)
- Upsert operations (add or update)

**Collections:**

- `knowledge_references`: For storing Islamic knowledge sources
- `journey_templates`: For storing user journey templates

**Usage:**

```python
chroma_service = ChromaDBService(persist_directory="./chromadb_data")
await chroma_service.connect()

# Search knowledge references
results = await chroma_service.search_knowledge_references(
    query="anxiety management",
    limit=5,
    category="STRATEGY"
)

# Search journey templates
templates = await chroma_service.search_journey_templates(
    query="morning routine habits",
    limit=5,
    active_only=True
)

# Get statistics
stats = await chroma_service.get_collection_stats()

await chroma_service.disconnect()
```

### 3. Sync Service (`app/services/sync_service.py`)

Orchestrates the synchronization process.

**Features:**

- Full sync mode (clears ChromaDB before syncing)
- Incremental sync mode (only new/updated items)
- Single item sync operations
- Document preparation and transformation
- Error handling with detailed logging
- Sync statistics tracking

**Document Preparation:**

For each data type, the service prepares documents by:

1. **KnowledgeReference:**

   - Combining title and content in all languages
   - Including category and tags
   - Creating searchable text for semantic embeddings
   - Preserving Arabic content for reference

2. **JourneyTemplate:**
   - Extracting goal keywords and tags
   - Parsing full JSON structure
   - Creating comprehensive searchable text
   - Including active status and match count

**Usage:**

```python
sync_service = SyncService()

# Full synchronization (clears ChromaDB first)
stats = await sync_service.sync_all(force_full_sync=True)

# Incremental synchronization
stats = await sync_service.sync_all(force_full_sync=False)

# Sync single items
await sync_service.sync_knowledge_reference("ref_id")
await sync_service.sync_journey_template("template_id")
```

## API Endpoints

### REST API

The sync service provides REST endpoints for programmatic access:

```bash
# Run synchronization
POST /api/v1/sync/run
{
  "force_full_sync": false
}

# Sync single knowledge reference
POST /api/v1/sync/knowledge-reference/{reference_id}

# Sync single journey template
POST /api/v1/sync/journey-template/{template_id}

# Get collection statistics
GET /api/v1/sync/stats

# Health check
GET /api/v1/sync/health
```

### Example Requests

**Full Sync:**

```bash
curl -X POST http://localhost:8000/api/v1/sync/run \
  -H "Content-Type: application/json" \
  -d '{"force_full_sync": true}'
```

**Incremental Sync:**

```bash
curl -X POST http://localhost:8000/api/v1/sync/run \
  -H "Content-Type: application/json" \
  -d '{"force_full_sync": false}'
```

**Get Stats:**

```bash
curl http://localhost:8000/api/v1/sync/stats
```

## CLI Usage

The sync service can be run as a command-line tool for cronjob integration:

```bash
# Full synchronization
python -m app.cli.sync full

# Incremental synchronization
python -m app.cli.sync incremental

# Show statistics
python -m app.cli.sync stats

# Sync single knowledge reference
python -m app.cli.sync ref <reference_id>

# Sync single journey template
python -m app.cli.sync template <template_id>
```

### Cronjob Setup

**Every 6 hours incremental sync:**

```cron
0 */6 * * * cd /path/to/hala-app && /path/to/venv/bin/python -m app.cli.sync incremental >> /var/log/hala-sync.log 2>&1
```

**Daily full sync at 2 AM:**

```cron
0 2 * * * cd /path/to/hala-app && /path/to/venv/bin/python -m app.cli.sync full >> /var/log/hala-sync.log 2>&1
```

**Weekly full sync on Sunday at 3 AM:**

```cron
0 3 * * 0 cd /path/to/hala-app && /path/to/venv/bin/python -m app.cli.sync full >> /var/log/hala-sync.log 2>&1
```

## Data Schema

### KnowledgeReference

```json
{
  "id": "ref_123",
  "type": "knowledge_reference",
  "category": "VERSE",
  "source": "QS. 2:216",
  "title": {
    "id": "Ketenangan Hati",
    "en": "Peace of Mind"
  },
  "content": {
    "id": "Isi konten...",
    "en": "Content..."
  },
  "content_ar": "محتوى عربي",
  "tags": ["patience", "trust", "faith"],
  "languages": ["id", "en"],
  "status": "VERIFIED",
  "searchable_text": "...",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### JourneyTemplate

```json
{
  "id": "template_456",
  "type": "journey_template",
  "goal_keyword": "anxiety management",
  "tags": ["anxiety", "mental-health", "coping"],
  "languages": ["id", "en"],
  "is_active": true,
  "status": "PUBLISHED",
  "match_count": 42,
  "searchable_text": "...",
  "full_json": { ... },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## Search Integration

Once data is synced, you can use ChromaDB for semantic search in your application:

```python
from app.services.chromadb_service import ChromaDBService

async def find_relevant_knowledge(user_query: str):
    """Find relevant knowledge for user query."""
    service = ChromaDBService()
    await service.connect()

    results = await service.search_knowledge_references(
        query=user_query,
        limit=5
    )

    await service.disconnect()
    return results
```

## Performance Considerations

1. **Batch Processing**: Sync service uses batch operations for better performance
2. **Connection Pooling**: PostgreSQL service uses connection pooling (1-10 connections)
3. **Caching**: Scope embeddings are cached in memory
4. **Async Operations**: All I/O operations are async

**Typical Sync Times:**

- Full sync: ~2-3 seconds per 100 records
- Incremental sync: ~0.1 second per record
- Single record sync: ~50-100ms

## Error Handling

The sync service includes comprehensive error handling:

1. Connection errors are logged and retried
2. Individual record errors don't stop the entire sync
3. Statistics track number of errors
4. Detailed logs are written to `./sync.log`

**Error Recovery:**

```python
try:
    stats = await sync_service.sync_all()
    if stats["errors"] > 0:
        logger.warning(f"Sync completed with {stats['errors']} errors")
except Exception as e:
    logger.error(f"Sync failed: {str(e)}")
```

## Monitoring

Monitor sync operations using:

1. **API Health Check:**

   ```bash
   curl http://localhost:8000/api/v1/sync/health
   ```

2. **Log File:**

   ```bash
   tail -f ./sync.log
   ```

3. **Statistics Endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/sync/stats
   ```

## Troubleshooting

### PostgreSQL Connection Failed

- Verify connection string in `.env`: `POSTGRES_URL`
- Check PostgreSQL service is running
- Verify database and table names match schema

### ChromaDB Issues

- Check `./chromadb_data` directory exists and is writable
- Verify ChromaDB version compatibility
- Try running with `force_full_sync=true`

### Slow Sync Performance

- Check PostgreSQL query performance
- Verify network connectivity
- Monitor CPU usage during sync

### Missing Data in ChromaDB

- Check PostgreSQL data status and filters
- Review error logs in `./sync.log`
- Verify document preparation logic
