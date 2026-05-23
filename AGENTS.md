# AGENTS.md

Guide for Codex and other coding agents working in `news-kg-api`.

This file keeps agent behavior consistent across branches, implementation work, tests, documentation, and project structure.

The project is a FastAPI + MongoDB backend that crawls TechCrunch OpenAI articles, extracts people and relationships with an LLM, stores them as a knowledge graph, and exposes the result through HTTP API endpoints.

Use the phrase **parallel article-processing pipeline** when describing the architecture.

Do not describe the project as a complex multi-agent framework. The project uses a service-based architecture with one LLM-powered analysis step.

---

## 1) Non-Negotiable Workflow

- Never start feature work directly on `main`.
- Always create or switch to a dedicated feature branch first.
- Use the branch prefix `codex/` unless the user asks for a different naming scheme.
- Keep scope tight. Do not mix unrelated fixes into the same branch.
- Read the surrounding code before editing.
- Match the existing project structure and naming style.
- Do not rewrite large parts of the project unless the task requires it.
- Do not introduce unnecessary frameworks or abstractions.
- Do not add LangChain, CrewAI, AutoGen, Celery, Redis, or Neo4j unless the user explicitly asks.
- Prefer simple, readable service classes over complicated agent abstractions.
- If a task touches API behavior, update request/response schemas and docs.
- If a task touches the LLM prompt or output format, update validation and tests.
- If a task touches MongoDB storage format, update repository code and related tests.
- Do not revert unrelated user changes.
- Keep commits logically grouped.

---

## 2) Definition of Done

A change is not done until all of the following are true:

- Relevant tests were added or updated.
- The implementation passes the relevant tests.
- `pytest -q` passes, or the smallest relevant tests pass first and then the suite is expanded.
- `pre-commit run --all-files` passes if pre-commit is configured.
- API schemas are updated if endpoint behavior changed.
- README or project docs are updated if architecture, setup, or behavior changed.
- The branch is clean.
- The diff only contains task-relevant changes.
- Any new environment variables are added to `.env.example`.
- Any new MongoDB indexes are created during app startup or documented clearly.

---

## 3) Main Stack

Use the following stack:

- Python 3.11+
- FastAPI
- MongoDB
- Motor for async MongoDB access
- Pydantic for request/response validation
- Pydantic Settings for configuration
- HTTPX for async HTTP requests
- BeautifulSoup and/or Trafilatura for crawling and article extraction
- OpenAI API or compatible LLM provider for structured extraction
- Pytest and pytest-asyncio for testing
- Docker Compose for local MongoDB

Avoid adding heavy dependencies unless clearly needed.

---

## 4) Repo-Specific Architecture Notes

Expected project structure:

```text
news-kg-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── articles.py
│   │   ├── rescan.py
│   │   └── people.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── article.py
│   │   ├── people.py
│   │   ├── relationship.py
│   │   └── rescan.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── crawler_service.py
│   │   ├── article_extractor_service.py
│   │   ├── llm_analysis_service.py
│   │   ├── graph_storage_service.py
│   │   └── pipeline_service.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── article_repository.py
│   │   ├── person_repository.py
│   │   └── relationship_repository.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── text.py
│   │   ├── normalization.py
│   │   └── exceptions.py
│   │
│   └── prompts/
│       └── graph_extraction_prompt.txt
│
├── tests/
├── evaluation/
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
└── README.md
```

Main app entrypoint:

```text
app/main.py
```

Config:

```text
app/config.py
```

Database connection:

```text
app/database.py
```

API routers:

```text
app/api/
```

Business logic:

```text
app/services/
```

MongoDB access:

```text
app/repositories/
```

Shared utilities:

```text
app/utils/
```

LLM prompt templates:

```text
app/prompts/
```

---

## 5) Core Pipeline

The main pipeline is:

```text
TechCrunch listing pages
    ↓
CrawlerService
    ↓
Article URLs
    ↓
PipelineService
    ↓
ArticleExtractorService
    ↓
Clean article data
    ↓
LLMAnalysisService
    ↓
Structured graph JSON
    ↓
GraphStorageService
    ↓
MongoDB
    ↓
FastAPI endpoints
```

Each article should be processed independently.

For `/rescan`, process multiple articles concurrently using `asyncio.gather`.

Use a semaphore to limit parallel LLM calls.

Example:

```python
semaphore = asyncio.Semaphore(settings.max_concurrent_articles)
```

Do not allow one failed article to stop the whole rescan.

Use `return_exceptions=True` when processing multiple articles concurrently.

---

## 6) Required API Endpoints

Implement and maintain these endpoints.

### Health Check

```http
GET /health
```

Returns:

```json
{
  "status": "ok"
}
```

### Process One Article

```http
POST /articles
```

Request:

```json
{
  "url": "https://techcrunch.com/..."
}
```

Expected behavior:

1. Validate the URL.
2. Fetch the article.
3. Extract clean article text.
4. Send article data to the LLM.
5. Validate the LLM response.
6. Store article, people, aliases, and relationships.
7. Return a processing summary.

Example response:

```json
{
  "url": "https://techcrunch.com/...",
  "status": "processed",
  "people_count": 5,
  "relationships_count": 8
}
```

### Rescan TechCrunch Pages

```http
POST /rescan
```

Request:

```json
{
  "pages": 2
}
```

Expected behavior:

1. Crawl TechCrunch OpenAI listing pages.
2. Extract article URLs.
3. Remove duplicate URLs.
4. Process articles concurrently.
5. Continue even if some articles fail.
6. Return a summary with successes and failures.

Example response:

```json
{
  "pages_scanned": 2,
  "urls_found": 20,
  "processed": 18,
  "failed": 2,
  "errors": [
    {
      "url": "https://techcrunch.com/...",
      "error": "Could not extract article text"
    }
  ]
}
```

### List People

```http
GET /people?page=1&limit=20
```

Expected behavior:

- Return paginated people.
- Include canonical name and aliases.
- Do not include full relationship details in the list endpoint.

Example response:

```json
{
  "page": 1,
  "limit": 20,
  "total": 45,
  "people": [
    {
      "id": "665f...",
      "canonical_name": "Sam Altman",
      "aliases": ["Altman", "OpenAI CEO"]
    }
  ]
}
```

### Get Person Details

```http
GET /people/{id}
```

Expected behavior:

- Return one person.
- Include aliases.
- Include direct incoming relationships.
- Include direct outgoing relationships.
- Include evidence for each relationship.

Example response:

```json
{
  "id": "665f...",
  "canonical_name": "Sam Altman",
  "aliases": ["Altman", "OpenAI CEO"],
  "relationships": {
    "outgoing": [],
    "incoming": []
  }
}
```

---

## 7) MongoDB Guidance

Use MongoDB collections as graph storage.

Expected collections:

```text
articles
people
relationships
```

### articles Collection

Use this collection for crawled article data.

Required fields:

```text
url
title
authors
published_at
text
created_at
updated_at
```

Important index:

```text
url unique
```

### people Collection

Use this collection for graph nodes.

Required fields:

```text
canonical_name
normalized_name
aliases
article_ids
created_at
updated_at
```

Important indexes:

```text
normalized_name unique
aliases
```

### relationships Collection

Use this collection for directed graph edges.

Required fields:

```text
source_person_id
source_name
target_person_id
target_name
type
normalized_type
explanation
evidence
created_at
```

Evidence must include:

```text
article_id
article_url
sentence
```

Important indexes:

```text
source_person_id
target_person_id
normalized_type
source_person_id + target_person_id + normalized_type + evidence.article_url
```

Do not embed all relationships inside person documents for the main implementation. Store relationships in a separate collection to keep querying and deduplication clearer.

---

## 8) Entity Resolution Rules

Entity resolution means making sure the same real person becomes one node.

Example:

```text
Sam Altman
Altman
OpenAI CEO
OpenAI's CEO
```

should map to:

```text
Sam Altman
```

Use a simple MVP strategy:

1. Normalize names.
2. Match by `normalized_name`.
3. Match by aliases.
4. Add new aliases using `$addToSet`.
5. Create a new person only if no match exists.

Normalization rules:

```text
- lowercase
- trim spaces
- collapse repeated spaces
- remove safe punctuation
```

Do not over-engineer entity resolution.

Avoid complex fuzzy matching unless the user explicitly asks.

---

## 9) Relationship Extraction Rules

Relationships are directed edges.

Example:

```text
Elon Musk → criticizes → Sam Altman
```

Every relationship must include:

```text
source person
target person
type
explanation
evidence sentence
article URL
```

Do not store relationships without evidence.

Do not create a relationship if the evidence sentence does not support it.

Deduplicate relationships using:

```text
source_person_id
target_person_id
normalized_type
article_url
evidence sentence
```

If the same relationship appears in another article with different evidence, it may be stored separately.

---

## 10) LLM Guidance

The LLM should be used only for structured extraction.

Do not use the LLM for normal database reads.

Do not use the LLM in `GET /people`.

Do not use the LLM in `GET /people/{id}`.

Use the LLM only in:

```text
POST /articles
POST /rescan
```

The LLM prompt must require valid JSON.

Expected LLM output shape:

```json
{
  "people": [
    {
      "name": "string",
      "aliases": ["string"]
    }
  ],
  "relationships": [
    {
      "source": "string",
      "target": "string",
      "type": "string",
      "explanation": "string",
      "evidence": "string"
    }
  ]
}
```

Prompt rules:

```text
- Return only valid JSON.
- Include article authors as people.
- Include only real people, not companies.
- Merge aliases when obvious.
- Every relationship must be directed.
- Every relationship must include evidence from the article.
- If there is no clear evidence, do not create the relationship.
```

Always validate LLM output before storing it.

Never trust raw LLM output directly.

---

## 11) Validation Rules

Before storing LLM output:

- Output must be valid JSON.
- `people` must be a list.
- `relationships` must be a list.
- Every person must have `name`.
- Every relationship must have `source`.
- Every relationship must have `target`.
- Every relationship must have `type`.
- Every relationship must have `explanation`.
- Every relationship must have `evidence`.
- Source and target should exist in the people list or be created as people before saving the relationship.
- Empty or unsupported relationships should be ignored.
- Invalid article results should be marked as failed and should not stop the whole batch.

Use Pydantic schemas for validation where possible.

---

## 12) Crawler and Extractor Guidance

The crawler should only collect article URLs from TechCrunch listing pages.

The article extractor should process one article URL at a time.

Use separation of responsibility:

```text
CrawlerService:
- listing page URL generation
- listing page fetching
- article URL extraction

ArticleExtractorService:
- article fetching
- title extraction
- author extraction
- published date extraction
- clean article text extraction
```

Prefer HTTPX for async HTTP requests.

Use Trafilatura for main text extraction.

Use BeautifulSoup for fallback parsing.

Set timeouts for all HTTP requests.

Handle failed pages gracefully.

Do not hardcode only one article URL.

---

## 13) Parallel Processing Rules

For `/rescan`, process articles concurrently.

Use:

```python
asyncio.gather(..., return_exceptions=True)
```

Use a semaphore:

```python
asyncio.Semaphore(settings.max_concurrent_articles)
```

Default recommended concurrency:

```text
MAX_CONCURRENT_ARTICLES=5
```

Do not send unlimited parallel LLM requests.

Return both successful and failed article results.

A failed article should produce an error entry, not crash the whole endpoint.

---

## 14) Testing Strategy

Default to test-first for feature work:

1. Add or update the smallest relevant test.
2. Run the smallest relevant test.
3. Implement the feature or fix.
4. Expand to nearby tests.
5. Finish with the full relevant suite.

Recommended commands:

```bash
pytest -q tests/test_graph_storage_service.py::test_does_not_duplicate_people
pytest -q tests/test_graph_storage_service.py
pytest -q
```

Minimum useful tests:

```text
- health endpoint works
- crawler extracts article URLs
- article extractor returns title/text for a sample article
- LLM output validator accepts valid JSON
- LLM output validator rejects invalid JSON
- graph storage does not duplicate people
- graph storage does not duplicate aliases
- graph storage does not duplicate relationships
- GET /people pagination works
- GET /people/{id} returns incoming and outgoing relationships
- POST /rescan continues if one article fails
```

Use mocked LLM responses in unit tests.

Do not call a real LLM in normal unit tests.

Do not require live TechCrunch pages in normal unit tests unless the test is clearly marked as integration.

---

## 15) Linting and Formatting

If pre-commit is configured, run:

```bash
pre-commit run --all-files
```

Recommended tools:

```text
ruff
ruff-format
markdownlint
standard pre-commit hooks
```

If pre-commit rewrites files, review the rewritten diff and rerun until it passes cleanly.

Do not ignore lint failures.

---

## 16) Environment Variables

Keep environment variables in `.env`.

Update `.env.example` whenever a new variable is introduced.

Expected variables:

```env
APP_NAME=news-kg-api
ENV=development

MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=news_kg

OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini

MAX_CONCURRENT_ARTICLES=5
REQUEST_TIMEOUT_SECONDS=30
```

Never commit real API keys.

Never commit real `.env` files.

---

## 17) Local Commands

Useful commands:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
docker compose up -d
uvicorn app.main:app --reload
pytest -q
pre-commit run --all-files
```

If `python` is not available locally, use:

```bash
python3
```

API docs:

```text
http://localhost:8000/docs
```

---

## 18) Docker Guidance

Use Docker Compose for local MongoDB.

Expected `docker-compose.yml`:

```yaml
services:
  mongo:
    image: mongo:7
    container_name: news-kg-mongo
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  mongo_data:
```

Do not require Docker for running the FastAPI app unless the user asks.

MongoDB can run in Docker while FastAPI runs locally.

---

## 19) Documentation Requirements

Update README when changing:

- project setup
- environment variables
- endpoint behavior
- MongoDB schema
- pipeline behavior
- LLM prompt format
- evaluation strategy
- known limitations

README should explain:

```text
- how the pipeline works
- why MongoDB was chosen
- how entity resolution works
- how relationship extraction works
- how to run the app
- how to test the app
- known limitations
- future improvements
```

When adding or changing endpoints, include:

```text
- endpoint path
- request body
- response body
- failure behavior
```

---

## 20) Evaluation Guidance

The project should include a simple evaluation plan.

Use files like:

```text
evaluation/sample_articles.json
evaluation/expected_people.json
evaluation/expected_relationships.json
evaluation/evaluation_notes.md
```

Suggested metrics:

```text
people precision
people recall
relationship precision
evidence coverage
duplicate rate
direction correctness
```

Relationship direction matters.

Example:

```text
Elon Musk → criticizes → Sam Altman
```

is different from:

```text
Sam Altman → criticizes → Elon Musk
```

Do not claim perfect extraction.

Document limitations clearly.

---

## 21) Change Discipline

- Read the existing code before editing.
- Prefer small changes.
- Prefer explicit code over clever code.
- Do not introduce a new abstraction layer unless it simplifies the project.
- Keep service responsibilities separate.
- Keep repositories focused on MongoDB access.
- Keep API routers thin.
- Keep business logic in services.
- Keep LLM prompt text in `app/prompts/`.
- Keep validation logic close to schemas or dedicated validator helpers.
- Keep tests close to the behavior being changed.
- Do not mix formatting-only changes with feature changes unless formatting is required by pre-commit.
- Do not remove existing tests unless they are clearly obsolete and replaced.

---

## 22) What Not To Do

Do not:

- Build a complex multi-agent system.
- Add LangChain unless explicitly requested.
- Add CrewAI unless explicitly requested.
- Add AutoGen unless explicitly requested.
- Add Celery unless explicitly requested.
- Add Redis unless explicitly requested.
- Add Neo4j unless explicitly requested.
- Store all relationships only inside people documents.
- Call a real LLM inside normal unit tests.
- Use the LLM for simple database reads.
- Store relationships without evidence.
- Ignore invalid LLM JSON.
- Let one failed article crash the whole `/rescan`.
- Commit `.env` or secrets.
- Hardcode API keys.
- Hardcode only one TechCrunch article.

---

## 23) Recommended Codex Checklist

Before coding:

- Check current branch.
- Check `git status`.
- Create or switch to a `codex/` feature branch.
- Read the related files before editing.
- Identify the smallest test to add or update first.
- Check whether the change touches:
  - API schema
  - MongoDB collection structure
  - LLM prompt
  - entity resolution
  - relationship deduplication
  - crawler behavior
  - docs

During coding:

- Keep API routers thin.
- Put business logic in services.
- Put MongoDB queries in repositories.
- Validate LLM output before saving.
- Add or update tests.
- Keep errors clear and user-facing responses stable.

Before finishing:

- Run relevant tests.
- Run `pytest -q`.
- Run `pre-commit run --all-files` if configured.
- Review `git diff --stat`.
- Review `git status`.
- Update README or `.env.example` if needed.
- Make sure the branch is ready for PR.

---

## 24) Final Architecture Summary

This project is a small data integration and knowledge graph pipeline.

Final architecture:

```text
FastAPI API layer
    ↓
PipelineService
    ↓
CrawlerService
    ↓
ArticleExtractorService
    ↓
LLMAnalysisService
    ↓
GraphStorageService
    ↓
MongoDB
```

The system processes multiple articles in parallel during rescans, extracts structured people and relationships using an LLM, stores them as graph nodes and directed edges in MongoDB, and exposes the result through paginated API endpoints.
