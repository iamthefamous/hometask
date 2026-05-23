  # News → People Knowledge Graph API

## 1. Project Goal

The goal of this project is to build a Python backend service that reads TechCrunch articles about OpenAI, extracts people and relationships between them, stores the result as a knowledge graph, and exposes the graph through an HTTP API.

The system is built with:

- FastAPI for the HTTP API
- MongoDB for storage
- Motor as the async MongoDB driver
- BeautifulSoup / Trafilatura for crawling and article extraction
- An LLM for extracting people and relationships
- AsyncIO for parallel article processing

The main idea is:

```text
TechCrunch pages
    ↓
Article URLs
    ↓
Parallel article processing
    ↓
Clean article text
    ↓
LLM structured extraction
    ↓
Validation and deduplication
    ↓
MongoDB knowledge graph
    ↓
HTTP API
```

---

## 2. High-Level Pipeline

The system is designed as a parallel article-processing pipeline.

Each article goes through three main stages:

```text
Stage 1: Article extraction
Stage 2: LLM graph analysis
Stage 3: Graph persistence
```

For `POST /rescan`, the backend first collects article URLs from TechCrunch listing pages. Then it processes many articles concurrently.

Example:

```text
POST /rescan
    ↓
CrawlerService gets article URLs
    ↓
PipelineService starts parallel jobs
    ↓
Article 1: extract → analyze → store
Article 2: extract → analyze → store
Article 3: extract → analyze → store
Article 4: extract → analyze → store
    ↓
Return processing summary
```

This gives the project an agentic-style architecture without making it unnecessarily complex.

The LLM is used as a structured extraction component, not as the whole application.

---

## 3. Main Services

### 3.1 CrawlerService

Responsibility:

- Visit TechCrunch OpenAI topic pages
- Extract article URLs
- Support configurable page count
- Avoid duplicate URLs

Input:

```json
{
  "pages": 2
}
```

Output:

```json
[
  "https://techcrunch.com/...",
  "https://techcrunch.com/..."
]
```

Example pages:

```text
https://techcrunch.com/tag/openai/
https://techcrunch.com/tag/openai/page/2/
```

---

### 3.2 ArticleExtractorService

Responsibility:

- Fetch one article URL
- Extract title
- Extract author or authors
- Extract published date
- Extract clean article text
- Keep the original article URL

Output example:

```json
{
  "url": "https://techcrunch.com/...",
  "title": "OpenAI announces...",
  "authors": ["Kyle Wiggers"],
  "published_at": "2026-05-10T00:00:00Z",
  "text": "Full cleaned article text..."
}
```

Recommended libraries:

```text
httpx
beautifulsoup4
trafilatura
```

`trafilatura` can be used to extract the main article text. BeautifulSoup can be used for fallback parsing and extracting links from listing pages.

---

### 3.3 LLMAnalysisService

Responsibility:

- Send article data to an LLM
- Ask the LLM to extract:
  - people
  - aliases
  - directed relationships
  - relationship type
  - explanation
  - evidence sentence
- Return strict JSON

The LLM should receive the article text and return structured data.

Expected output:

```json
{
  "people": [
    {
      "name": "Sam Altman",
      "aliases": ["Altman", "OpenAI CEO"]
    },
    {
      "name": "Elon Musk",
      "aliases": ["Musk"]
    }
  ],
  "relationships": [
    {
      "source": "Elon Musk",
      "target": "Sam Altman",
      "type": "criticizes",
      "explanation": "Musk criticized Altman's role at OpenAI.",
      "evidence": "Musk criticized OpenAI CEO Sam Altman...",
      "article_url": "https://techcrunch.com/..."
    }
  ]
}
```

The LLM must be asked to return only valid JSON.

---

### 3.4 GraphStorageService

Responsibility:

- Store articles
- Store people as graph nodes
- Store aliases
- Store relationships as directed graph edges
- Avoid duplicate people
- Avoid duplicate relationships
- Attach provenance to every relationship

Main logic:

```text
1. Save or update article.
2. For each extracted person:
   - Normalize name.
   - Check if person already exists by canonical name or alias.
   - If exists, update aliases.
   - If not, create new person.
3. For each relationship:
   - Resolve source person.
   - Resolve target person.
   - Check for duplicate relationship.
   - Save edge with evidence and article reference.
```

---

### 3.5 PipelineService

Responsibility:

- Coordinate the whole pipeline
- Process one article
- Process many articles in parallel
- Handle partial failures

Single article flow:

```text
URL
 ↓
ArticleExtractorService.extract(url)
 ↓
LLMAnalysisService.analyze(article)
 ↓
GraphStorageService.save(article, graph_data)
 ↓
Processing result
```

Parallel flow:

```text
urls = crawler.get_article_urls(pages)
results = asyncio.gather(process_article(url) for url in urls)
```

The pipeline should not fail completely if one article fails. It should continue processing the remaining articles.

---

## 4. Project Structure

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
│   ├── test_crawler_service.py
│   ├── test_article_extractor_service.py
│   ├── test_graph_storage_service.py
│   └── test_people_api.py
│
├── evaluation/
│   ├── sample_articles.json
│   ├── expected_people.json
│   ├── expected_relationships.json
│   └── evaluation_notes.md
│
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 5. MongoDB Collections

MongoDB will store the graph using separate collections.

### 5.1 articles Collection

Stores crawled articles.

```json
{
  "_id": "ObjectId",
  "url": "https://techcrunch.com/...",
  "title": "OpenAI announces...",
  "authors": ["Kyle Wiggers"],
  "published_at": "2026-05-10T00:00:00Z",
  "text": "Clean article text...",
  "created_at": "2026-05-22T10:00:00Z",
  "updated_at": "2026-05-22T10:00:00Z"
}
```

Indexes:

```text
url unique
published_at
```

### 5.2 people Collection

Stores canonical people.

```json
{
  "_id": "ObjectId",
  "canonical_name": "Sam Altman",
  "normalized_name": "sam altman",
  "aliases": ["Altman", "OpenAI CEO"],
  "article_ids": ["ObjectId"],
  "created_at": "2026-05-22T10:00:00Z",
  "updated_at": "2026-05-22T10:00:00Z"
}
```

Indexes:

```text
normalized_name unique
aliases
```

### 5.3 relationships Collection

Stores directed graph edges.

```json
{
  "_id": "ObjectId",
  "source_person_id": "ObjectId",
  "source_name": "Elon Musk",
  "target_person_id": "ObjectId",
  "target_name": "Sam Altman",
  "type": "criticizes",
  "normalized_type": "criticizes",
  "explanation": "Musk criticized Altman's role at OpenAI.",
  "evidence": {
    "article_id": "ObjectId",
    "article_url": "https://techcrunch.com/...",
    "sentence": "Musk criticized OpenAI CEO Sam Altman..."
  },
  "created_at": "2026-05-22T10:00:00Z"
}
```

Indexes:

```text
source_person_id
target_person_id
type
source_person_id + target_person_id + normalized_type + evidence.article_url
```

---

## 6. Entity Resolution Strategy

Entity resolution means making sure one real person becomes one node.

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

For MVP, the system will use a simple strategy.

### Step 1: Normalize names

Normalization rules:

```text
- lowercase
- trim spaces
- remove extra spaces
- remove punctuation where safe
```

Example:

```text
" Sam Altman " → "sam altman"
"Altman" → "altman"
```

### Step 2: Match by canonical name

If `normalized_name` already exists, use the existing person.

### Step 3: Match by aliases

If an alias already exists in another person document, use that person.

### Step 4: Add aliases

If the person exists, add new aliases using `$addToSet`.

### Step 5: Create new person

If there is no match, create a new person.

This is intentionally simple. The task does not require a perfect large-scale entity-resolution system.

---

## 7. Relationship Resolution Strategy

Relationships are directed edges.

Example:

```text
Elon Musk → criticizes → Sam Altman
```

Each relationship must have:

```text
source person
target person
relationship type
explanation
article URL
evidence sentence
```

Deduplication rule:

A relationship is considered duplicate if these fields are the same:

```text
source_person_id
target_person_id
normalized_type
article_url
evidence sentence
```

If the same relationship appears in another article, it can be stored as another edge with different evidence.

If needed later, multiple evidence records can be grouped under one relationship.

---

## 8. API Endpoints

### 8.1 POST /articles

Processes one article URL.

Request:

```json
{
  "url": "https://techcrunch.com/..."
}
```

Flow:

```text
1. Validate URL.
2. Fetch article.
3. Extract article text.
4. Send article to LLM.
5. Validate LLM JSON.
6. Store article.
7. Store people.
8. Store relationships.
9. Return processing summary.
```

Response:

```json
{
  "url": "https://techcrunch.com/...",
  "status": "processed",
  "people_count": 5,
  "relationships_count": 8
}
```

### 8.2 POST /rescan

Crawls TechCrunch OpenAI pages and processes articles in parallel.

Request:

```json
{
  "pages": 2
}
```

Flow:

```text
1. Build listing page URLs.
2. Extract article URLs.
3. Remove duplicate URLs.
4. Process article URLs concurrently.
5. Store successful results.
6. Return summary.
```

Response:

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

### 8.3 GET /people

Lists all people with pagination.

Query parameters:

```text
page
limit
```

Example:

```text
GET /people?page=1&limit=20
```

Response:

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

### 8.4 GET /people/{id}

Returns one person with direct relationships.

Example:

```text
GET /people/665f...
```

Response:

```json
{
  "id": "665f...",
  "canonical_name": "Sam Altman",
  "aliases": ["Altman", "OpenAI CEO"],
  "relationships": {
    "outgoing": [
      {
        "target_person_id": "665a...",
        "target_name": "Satya Nadella",
        "type": "partners_with",
        "explanation": "Altman works with Nadella through the OpenAI and Microsoft partnership.",
        "evidence": {
          "article_url": "https://techcrunch.com/...",
          "sentence": "..."
        }
      }
    ],
    "incoming": [
      {
        "source_person_id": "665b...",
        "source_name": "Elon Musk",
        "type": "criticizes",
        "explanation": "Musk criticized Altman.",
        "evidence": {
          "article_url": "https://techcrunch.com/...",
          "sentence": "..."
        }
      }
    ]
  }
}
```

---

## 9. Parallel Processing Design

The `/rescan` endpoint should process articles concurrently.

Recommended approach:

```python
results = await asyncio.gather(
    *[pipeline_service.process_article(url) for url in urls],
    return_exceptions=True
)
```

Why this is useful:

```text
- Article fetching is I/O-heavy.
- LLM calls are I/O-heavy.
- Multiple articles can be processed independently.
- One failed article should not stop the whole rescan.
```

To avoid too many parallel LLM calls, use a semaphore:

```python
semaphore = asyncio.Semaphore(5)
```

This means only 5 articles are processed at the same time.

Example logic:

```python
async def process_with_limit(url: str):
    async with semaphore:
        return await process_article(url)
```

This protects the app from rate limits and overload.

---

## 10. LLM Prompt Design

The LLM prompt should be strict.

It should say:

```text
You are an information extraction system.

Extract people and relationships from the article.

Rules:
- Return only valid JSON.
- Include article authors as people.
- Include only real people, not companies.
- Merge aliases when obvious.
- Every relationship must be directed.
- Every relationship must include evidence from the article.
- If there is no clear evidence, do not create the relationship.
```

Expected JSON schema:

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

---

## 11. Validation After LLM

The backend must validate LLM output before storing it.

Validation rules:

```text
- Output must be valid JSON.
- people must be a list.
- relationships must be a list.
- Every person must have name.
- Every relationship must have source.
- Every relationship must have target.
- Every relationship must have type.
- Every relationship must have explanation.
- Every relationship must have evidence.
- Source and target must exist in people list or be added automatically.
```

If validation fails:

```text
- Mark article as failed.
- Save error message.
- Continue processing other articles.
```

---

## 12. Why MongoDB Is Acceptable

MongoDB is acceptable because article data and LLM output can be semi-structured.

Advantages:

```text
- Easy to store raw article data.
- Easy to store aliases as arrays.
- Easy to store evidence as nested objects.
- Flexible if LLM output changes.
- Good for fast MVP development.
```

Tradeoff:

```text
- Graph queries are not as natural as in Neo4j.
- Joins are not as clean as SQL.
- Deduplication must be handled carefully in application code.
```

Decision:

```text
For this MVP, MongoDB is used because it gives flexibility for messy article data and LLM-generated structured output. The graph is represented using people documents as nodes and relationship documents as directed edges.
```

---

## 13. Extensibility Plan

The project should be designed so other news websites can be added later.

Use a crawler interface:

```python
class BaseCrawler:
    async def get_article_urls(self, pages: int) -> list[str]:
        raise NotImplementedError
```

Then TechCrunch has its own implementation:

```python
class TechCrunchCrawler(BaseCrawler):
    async def get_article_urls(self, pages: int) -> list[str]:
        ...
```

Later, another source can be added:

```python
class TheVergeCrawler(BaseCrawler):
    async def get_article_urls(self, pages: int) -> list[str]:
        ...
```

The rest of the pipeline stays the same.

---

## 14. Evaluation Strategy

Relationship extraction does not have only one correct answer, so the project needs an evaluation plan.

The evaluation will use a small manually checked dataset.

Files:

```text
evaluation/sample_articles.json
evaluation/expected_people.json
evaluation/expected_relationships.json
```

Metrics:

```text
1. People precision
   How many extracted people are actually correct?

2. People recall
   How many expected people were found?

3. Relationship precision
   How many extracted relationships are reasonable and supported by evidence?

4. Evidence coverage
   What percentage of relationships have evidence sentences?

5. Duplicate rate
   How many duplicate people or relationships were created?

6. Direction correctness
   Is the relationship direction correct?
```

Example:

```text
Elon Musk → criticizes → Sam Altman
```

is different from:

```text
Sam Altman → criticizes → Elon Musk
```

So direction matters.

---

## 15. Error Handling

The system should handle these failures:

```text
- TechCrunch page unavailable
- Article URL invalid
- Article text cannot be extracted
- LLM returns invalid JSON
- LLM misses people
- MongoDB insert fails
- Duplicate article already exists
```

Each article should have an independent result.

One article failure should not stop the whole `/rescan`.

---

## 16. Environment Variables

Example `.env`:

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

---

## 17. Requirements

Example `requirements.txt`:

```text
fastapi
uvicorn[standard]
motor
pydantic
pydantic-settings
python-dotenv
httpx
beautifulsoup4
trafilatura
openai
pytest
pytest-asyncio
```

---

## 18. Docker Compose for MongoDB

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

Run MongoDB:

```bash
docker compose up -d
```

---

## 19. Running the App

Install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run MongoDB:

```bash
docker compose up -d
```

Run FastAPI:

```bash
uvicorn app.main:app --reload
```

Open docs:

```text
http://localhost:8000/docs
```

---

## 20. Development Order

### Step 1: Basic FastAPI Setup

Create:

```text
app/main.py
app/config.py
app/database.py
```

Make sure this works:

```text
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

### Step 2: Connect MongoDB

Create database connection using Motor.

Test that app can connect to MongoDB.

### Step 3: Build Article Extraction

Create:

```text
ArticleExtractorService
```

Test with one TechCrunch article URL.

Goal:

```text
URL → title, authors, published date, text
```

### Step 4: Build Crawler

Create:

```text
CrawlerService
TechCrunchCrawler
```

Goal:

```text
pages = 2 → list of article URLs
```

### Step 5: Build LLM Analysis

Create:

```text
LLMAnalysisService
```

Goal:

```text
article text → structured JSON
```

At this stage, print the LLM response before storing anything.

### Step 6: Build Graph Storage

Create:

```text
GraphStorageService
PersonRepository
ArticleRepository
RelationshipRepository
```

Goal:

```text
structured JSON → MongoDB graph
```

### Step 7: Build POST /articles

Goal:

```text
single URL → process article → store graph
```

### Step 8: Build POST /rescan

Goal:

```text
pages → crawl URLs → process articles in parallel
```

Use:

```python
asyncio.gather(..., return_exceptions=True)
```

### Step 9: Build GET /people

Goal:

```text
paginated people list
```

### Step 10: Build GET /people/{id}

Goal:

```text
person details + incoming relationships + outgoing relationships
```

### Step 11: Add Tests

Minimum useful tests:

```text
- crawler extracts article URLs
- article extractor returns text
- graph storage does not duplicate people
- graph storage does not duplicate relationships
- GET /people pagination works
```

### Step 12: Write README

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

---

## 21. Known Limitations

For the first version, these limitations are acceptable:

```text
- Entity resolution is simple and rule-based.
- LLM extraction may miss some relationships.
- Relationship vocabulary is not fixed globally.
- MongoDB is not a true graph database.
- Some TechCrunch pages may have different HTML structure.
- Evidence quality depends on article extraction quality.
```

---

## 22. Future Improvements

Possible improvements:

```text
- Add fixed relationship taxonomy.
- Add better alias resolution.
- Add human review mode for uncertain relationships.
- Add background workers with Celery or RQ.
- Add Redis queue for large rescans.
- Add Neo4j if graph queries become complex.
- Add confidence scores from the LLM.
- Add UI for graph visualization.
```

---

## 23. Final Architecture Summary

This project is not just a simple scraper.

It is a small data integration and knowledge graph pipeline.

The final architecture is:

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

The system processes multiple articles in parallel during rescans, extracts structured people and relationships using an LLM, stores them as graph nodes and edges in MongoDB, and exposes the result through paginated API endpoints.

Use the phrase **parallel article-processing pipeline** instead of **many agents**. It sounds more professional and more accurate.
