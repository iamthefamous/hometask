import pytest

from app.schemas.article import ArticleData
from app.schemas.llm import LLMGraphOutput
from app.services.graph_storage_service import GraphStorageService


class _ArticleRepo:
    async def ensure_indexes(self):
        return None

    async def upsert_article(self, _article):
        return "a1"


class _PersonRepo:
    def __init__(self):
        self.names = {}
        self.counter = 0

    async def ensure_indexes(self):
        return None

    async def upsert_person(self, canonical_name, aliases, article_id):
        key = canonical_name.lower()
        if key not in self.names:
            self.counter += 1
            self.names[key] = f"p{self.counter}"
        return self.names[key]


class _RelationshipRepo:
    def __init__(self):
        self.rows = set()

    async def ensure_indexes(self):
        return None

    async def insert_relationship_if_not_exists(self, **kwargs):
        key = (
            kwargs["source_person_id"],
            kwargs["target_person_id"],
            kwargs["relationship_type"].lower(),
            kwargs["article_url"],
            kwargs["sentence"],
        )
        if key in self.rows:
            return False
        self.rows.add(key)
        return True


@pytest.mark.asyncio
async def test_does_not_duplicate_relationships():
    service = GraphStorageService(_ArticleRepo(), _PersonRepo(), _RelationshipRepo())
    article = ArticleData(url="https://techcrunch.com/x", text="t", title="x", authors=[])
    graph = LLMGraphOutput.model_validate(
        {
            "people": [{"name": "Sam Altman", "aliases": ["Altman"]}, {"name": "Elon Musk", "aliases": []}],
            "relationships": [
                {
                    "source": "Elon Musk",
                    "target": "Sam Altman",
                    "type": "criticizes",
                    "explanation": "x",
                    "evidence": "musk criticized altman",
                },
                {
                    "source": "Elon Musk",
                    "target": "Sam Altman",
                    "type": "criticizes",
                    "explanation": "x",
                    "evidence": "musk criticized altman",
                },
            ],
        }
    )

    people_count, relationships_count = await service.save_graph(article, graph)

    assert people_count == 2
    assert relationships_count == 1


@pytest.mark.asyncio
async def test_filters_noisy_people_names():
    service = GraphStorageService(_ArticleRepo(), _PersonRepo(), _RelationshipRepo())
    article = ArticleData(url="https://techcrunch.com/x", text="t", title="x", authors=[])
    graph = LLMGraphOutput.model_validate(
        {
            "people": [
                {"name": "Sam Altman", "aliases": ["OpenAI CEO"]},
                {
                    "name": "Aisha Malik Consumer News Reporter Aisha is a consumer news reporter at TechCrunch. View Bio",
                    "aliases": [],
                },
            ],
            "relationships": [],
        }
    )

    people_count, relationships_count = await service.save_graph(article, graph)

    assert people_count == 2
    assert relationships_count == 0
