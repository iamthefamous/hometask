# news-kg-api

FastAPI service that crawls TechCrunch OpenAI articles, extracts people and directed relationships, stores them in MongoDB, and serves them through HTTP endpoints.

## Architecture

The system is a **parallel article-processing pipeline**:

```text
TechCrunch listing pages
  -> CrawlerService
  -> PipelineService
  -> ArticleExtractorService
  -> LLMAnalysisService
  -> GraphStorageService
  -> MongoDB
  -> FastAPI endpoints
```

## Why MongoDB

MongoDB works well for this MVP because articles, people, and relationships are naturally document-shaped, index support is strong, and schema evolution is straightforward.

## Endpoints

- `GET /health`
  - Response: `{ "status": "ok" }`

- `POST /articles`
  - Request:
    ```json
    { "url": "https://techcrunch.com/..." }
    ```
  - Response:
    ```json
    {
      "url": "https://techcrunch.com/...",
      "status": "processed",
      "people_count": 5,
      "relationships_count": 8
    }
    ```

- `POST /rescan`
  - Request:
    ```json
    { "pages": 2 }
    ```
  - Failure behavior: continues processing when one article fails and reports per-URL errors.

- `GET /people?page=1&limit=20`
  - Returns paginated people with aliases.

- `GET /people/{id}`
  - Returns one person with incoming and outgoing relationships and evidence.

## Entity Resolution

MVP strategy:
1. Normalize names (`lowercase`, trim, collapse spaces, remove safe punctuation).
2. Match by `normalized_name`.
3. Match by aliases.
4. Add aliases with `$addToSet`.
5. Create new person only if no match exists.

## Relationship Extraction

Each relationship is directed and stores:
- `source`, `target`, `type`, `explanation`
- evidence: `article_id`, `article_url`, `sentence`

Deduplication key:
- `source_person_id + target_person_id + normalized_type + article_url + sentence`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## Testing

```bash
pytest -q
```

Unit tests use mocked dependencies and do not call a real LLM.

## Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

## LLM Provider Setup

`gpt-4o-mini` via OpenAI requires an API key. For free local usage, run Ollama and set:

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=qwen2.5:7b-instruct
LLM_API_KEY=
```

Keep `LLM_PROVIDER=mock` if you want a test-only path with no external model call.

## Known Limitations

- LLM output quality depends on the selected model and prompt adherence.
- Entity resolution is intentionally simple and may miss ambiguous cases.
- Crawler parsing depends on TechCrunch page structure and may need maintenance.

## Data Cleanup

If historical scans inserted noisy person records (bios/job-title text), run:

```bash
python scripts/cleanup_noisy_people.py
```

This is a dry-run and prints what would be removed.

To apply deletion:

```bash
python scripts/cleanup_noisy_people.py --apply
```

To convert long canonical names into short canonical names and keep long variants as aliases:

```bash
python scripts/normalize_people_to_short_names.py
python scripts/normalize_people_to_short_names.py --apply
```

To drop only graph collections (`articles`, `people`, `relationships`) while keeping the database:

```bash
python scripts/drop_graph_collections.py
python scripts/drop_graph_collections.py --apply
```

To drop the entire configured MongoDB database:

```bash
python scripts/drop_database.py
python scripts/drop_database.py --apply
```

## Future Improvements

- Add robust LLM provider integration with retries and JSON schema enforcement.
- Add integration tests with fixture HTML snapshots.
- Add stronger alias resolution and confidence scoring.
