# Hala AI Service

A multi-layer AI pipeline service for generating personalized Islamic spiritual and productivity journeys.

## 🏗️ Architecture

This service implements a 5-layer pipeline architecture:

```
User Input → Layer 1 → Layer 2 → Layer 3 → Layer 4 → Layer 5 → Response
              │          │          │          │          │
              ▼          ▼          ▼          ▼          ▼
          Sanitize   Semantic    Safety      RAG       LLM
                     Validate   Guardrails  Retrieval  Inference
```

### Project Structure

```
app/
├── api/                    # API Layer (Routes/Controllers)
│   ├── v1/
│   │   ├── endpoints/      # Route handlers
│   │   │   ├── health.py   # Health check endpoints
│   │   │   └── journey.py  # Journey generation endpoints
│   │   └── schemas/        # Pydantic request/response models
│   └── deps.py             # Dependency injection
├── core/                   # Core configurations
│   ├── config.py           # Settings & environment
│   ├── exceptions.py       # Custom exceptions
│   └── responses.py        # Standardized responses
├── pipelines/              # Multi-layer pipeline (Layers 1-5)
│   ├── base.py             # Abstract pipeline layer
│   ├── layer1_sanitization.py
│   ├── layer2_semantic.py
│   ├── layer3_safety.py
│   ├── layer4_rag.py
│   ├── layer5_inference.py
│   └── orchestrator.py     # Pipeline coordinator
├── providers/              # LLM Providers (Strategy Pattern)
│   ├── base.py             # Abstract LLM provider
│   ├── gemini.py           # Google Gemini
│   ├── openai.py           # OpenAI GPT
│   ├── ollama.py           # Local Ollama
│   └── factory.py          # Provider factory
├── services/               # Business logic services
│   ├── embedding_service.py
│   └── knowledge_sync_service.py
├── db/                     # Database layer
│   ├── postgresql/         # PostgreSQL connection & models
│   └── vector/             # ChromaDB for RAG
├── utils/                  # Utilities
│   └── logging.py
└── main.py                 # FastAPI entry point
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Gemini API Key (or other LLM provider)

### Installation

1. **Clone and setup environment**

```bash
cd hala-ai
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Initialize database**

```bash
# Create PostgreSQL database
createdb hala_ai

# Run migrations (when implemented)
alembic upgrade head
```

4. **Run the service**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Access the API**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/v1/health

## 📡 API Endpoints

### Health

- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health with all dependencies
- `GET /api/v1/health/providers` - List LLM providers status

### Journey

- `POST /api/v1/journey/generate` - Generate a personalized journey
- `POST /api/v1/journey/validate` - Validate input without generating

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/journey/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Saya ingin meningkatkan kebiasaan sholat tahajud",
    "language": "id"
  }'
```

## 🧠 Pipeline Layers

### Layer 1: Sanitization

- Input length validation (10-500 chars)
- Prompt injection detection
- Profanity filtering

### Layer 2: Semantic Validation

- Uses Sentence-Transformers (all-MiniLM-L6-v2)
- Cosine similarity check against official scopes
- Threshold: 0.45

### Layer 3: Safety Guardrails

- Crisis/self-harm detection with help resources
- Violence detection
- Haram topics filtering

### Layer 4: RAG Retrieval

- ChromaDB vector search
- Retrieves Quran verses, Hadith, Hala strategies
- Top-K results (default: 5)

### Layer 5: LLM Inference

- Supports multiple providers (Gemini, OpenAI, Ollama)
- JSON response format
- 14-day journey generation

## 🔌 Adding New LLM Provider

1. Create new provider in `app/providers/`

```python
from app.providers.base import BaseLLMProvider

class MyProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "my_provider"

    async def generate(self, ...): ...
    async def health_check(self) -> bool: ...
```

2. Register in factory

```python
# app/providers/factory.py
from app.providers.my_provider import MyProvider

class LLMProviderFactory:
    _providers = {
        "my_provider": MyProvider,
        ...
    }
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## 📝 License

Proprietary - Hala Journal
