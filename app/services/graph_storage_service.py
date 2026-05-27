from app.repositories.article_repository import ArticleRepository
from app.repositories.person_repository import PersonRepository
from app.repositories.relationship_repository import RelationshipRepository
from app.schemas.article import ArticleData
from app.schemas.llm import LLMGraphOutput
from app.schemas.people import PersonExtraction
from app.utils.normalization import (
    extract_canonical_person_name,
    looks_like_bio_or_metadata,
)


class GraphStorageService:
    def __init__(
        self,
        article_repo: ArticleRepository,
        person_repo: PersonRepository,
        relationship_repo: RelationshipRepository,
    ):
        self.article_repo = article_repo
        self.person_repo = person_repo
        self.relationship_repo = relationship_repo

    async def ensure_indexes(self) -> None:
        await self.article_repo.ensure_indexes()
        await self.person_repo.ensure_indexes()
        await self.relationship_repo.ensure_indexes()

    async def save_graph(
        self, article: ArticleData, graph: LLMGraphOutput
    ) -> tuple[int, int]:
        article_id = await self.article_repo.upsert_article(article.model_dump())
        extracted_people = list(graph.people)
        known_names = {
            person.name.strip().lower()
            for person in extracted_people
            if person.name.strip()
        }
        for author in article.authors:
            cleaned = author.strip()
            if not cleaned:
                continue
            if cleaned.lower() in known_names:
                continue
            extracted_people.append(PersonExtraction(name=cleaned, aliases=[]))
            known_names.add(cleaned.lower())

        people_map: dict[str, str] = {}
        for person in extracted_people:
            if looks_like_bio_or_metadata(person.name):
                continue
            canonical_name = extract_canonical_person_name(person.name)
            if not canonical_name:
                continue
            aliases = [
                alias.strip()
                for alias in person.aliases
                if alias.strip() and not looks_like_bio_or_metadata(alias)
            ]
            if person.name != canonical_name:
                aliases.append(person.name)
            person_id = await self.person_repo.upsert_person(
                canonical_name=canonical_name,
                aliases=aliases,
                article_id=article_id,
            )
            people_map[person.name] = person_id
            people_map[canonical_name] = person_id

        relationships_count = 0
        for rel in graph.relationships:
            source_name = extract_canonical_person_name(rel.source)
            target_name = extract_canonical_person_name(rel.target)
            if not source_name or not target_name:
                continue
            source_id = people_map.get(rel.source) or people_map.get(source_name)
            if not source_id:
                source_aliases = [rel.source] if rel.source != source_name else []
                source_id = await self.person_repo.upsert_person(
                    source_name, source_aliases, article_id
                )
                people_map[rel.source] = source_id
                people_map[source_name] = source_id

            target_id = people_map.get(rel.target) or people_map.get(target_name)
            if not target_id:
                target_aliases = [rel.target] if rel.target != target_name else []
                target_id = await self.person_repo.upsert_person(
                    target_name, target_aliases, article_id
                )
                people_map[rel.target] = target_id
                people_map[target_name] = target_id

            inserted = await self.relationship_repo.insert_relationship_if_not_exists(
                source_person_id=source_id,
                source_name=source_name,
                target_person_id=target_id,
                target_name=target_name,
                relationship_type=rel.type,
                explanation=rel.explanation,
                article_id=article_id,
                article_url=str(article.url),
                sentence=rel.evidence,
            )
            if inserted:
                relationships_count += 1

        return len(set(people_map.values())), relationships_count
