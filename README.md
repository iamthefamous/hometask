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

## Gemini LLM Setup

Gemini uses the official Google Gen AI SDK:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
```

`GEMINI_MODEL` is optional and defaults to `gemini-3.1-flash-lite`. The
pipeline uses Gemini only for LLM analysis.

Limit concurrent article workers in the parallel article-processing pipeline with:

```env
MAX_CONCURRENT_ARTICLES=5
```

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



## Possible Future Improvements

### Product Improvements

- Add graph visualization.
- Add search by person name.
- Add search by relationship type.
- Add article-level graph view.
- Add confidence scores for relationships.
- Add manual review/editing interface.
- Add support for more news sources.
- Add source credibility metadata.
### Engineering Improvements

- Add background job queue.
- Add Redis caching.
- Add structured logs.
- Add OpenAPI examples.
- Add better test coverage.

### AI Improvements

- Improve extraction prompt.
- Add fixed relationship taxonomy.
- Add validation prompt.
- Add retry handling for transient Gemini API failures.
- Add extraction evaluation dataset.
- Add confidence scoring.
- Add hallucination filters.

---

## Development Process

This project was implemented with the help of **Codex 5.3 Agent**.

Before implementation, I prepared project planning documents to guide the development process.

### `AGENTS.md`

I wrote `AGENTS.md` to define how the coding agent should work on the project.

It includes:

- project rules
- implementation requirements
- coding standards
- expected behavior
- definition of done
- testing expectations
- architectural constraints
- instructions for safe and consistent changes

This file helped keep the implementation structured and consistent across the project.

### `info.md`

I also wrote `info.md` as a brainstorming and planning document.

It includes:

- the main project idea
- expected API endpoints
- the project pipeline
- technology choices
- justification for using FastAPI
- justification for using MongoDB
- how articles should be crawled and processed
- how the LLM should extract people and relationships
- how the extracted graph data should be stored
- possible limitations and future improvements

This document was used as the initial project design before implementation.

### AI-Assisted Development Note

The project was not generated randomly by an AI tool.

The development process followed my own planning documents, project requirements, and architectural decisions. Codex 5.3 Agent was used as an implementation assistant to speed up development, generate code, and help connect the different parts of the system.

The main design decisions, pipeline structure, endpoint planning, and requirements were prepared in advance through `AGENTS.md` and `info.md`.
