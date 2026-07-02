import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.schemas import Recommendation


DATA_FILE = Path(__file__).resolve().parent / "catalog.json"


@dataclass
class CatalogEntry:
    name: str
    url: str
    test_type: str
    description: str
    job_levels: list[str]
    keywords: list[str]
    roles: list[str]
    skills: list[str]

    @classmethod
    def from_dict(cls, item: dict) -> "CatalogEntry":
        return cls(
            name=item["name"],
            url=item["url"],
            test_type=item["test_type"],
            description=item.get("description", ""),
            job_levels=item.get("job_levels", []),
            keywords=item.get("keywords", []),
            roles=item.get("roles", []),
            skills=item.get("skills", []),
        )


class Catalog:
    def __init__(self, data_file: Optional[Path] = None) -> None:
        self.data_file = data_file or DATA_FILE
        self.items = self._load_catalog()

    def _load_catalog(self) -> list[CatalogEntry]:
        if not self.data_file.exists():
            return []
        with self.data_file.open("r", encoding="utf-8") as handle:
            raw_items = json.load(handle)
        return [CatalogEntry.from_dict(item) for item in raw_items]

    def search(self, profile: dict, limit: int = 10) -> list[Recommendation]:
        scored: list[tuple[int, CatalogEntry]] = []
        for item in self.items:
            score = self._score_item(item, profile)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda entry: (-entry[0], entry[1].name))
        if not scored:
            return []

        max_score = max(score for score, _ in scored)
        top_results = scored[:limit]
        return [self._to_recommendation(item, self._to_confidence(score, max_score)) for score, item in top_results]

    def find_assessments_in_text(self, text: str, limit: int = 10) -> list[Recommendation]:
        normalized_text = self._normalize(text)
        matches: list[Recommendation] = []
        seen: set[str] = set()

        for item in self.items:
            normalized_name = self._normalize(item.name)
            short_name = normalized_name.replace("shl ", "", 1)
            if normalized_name in normalized_text or short_name in normalized_text:
                if item.url not in seen:
                    matches.append(self._to_recommendation(item, 1.0))
                    seen.add(item.url)

        return matches[:limit]

    def _score_item(self, item: CatalogEntry, profile: dict) -> int:
        score = 0

        if profile.get("role"):
            score += self._keyword_overlap([profile["role"]], item.roles, 5)

        if profile.get("seniority"):
            score += self._keyword_overlap([profile["seniority"]], item.job_levels, 4)

        test_types = profile.get("test_types", [])
        if test_types:
            score += self._keyword_overlap(test_types, [item.test_type], 6)

        skills = profile.get("skills", [])
        if skills:
            score += self._keyword_overlap(skills, item.skills + item.keywords, 4)

        if item.test_type in test_types:
            score += 3

        return score

    def _keyword_overlap(self, needles: list[str], haystack: list[str], weight: int) -> int:
        normalized_haystack = {self._normalize(value) for value in haystack}
        total = 0
        for needle in needles:
            if self._normalize(needle) in normalized_haystack:
                total += weight
        return total

    def _to_recommendation(self, item: CatalogEntry, confidence: float | None = None) -> Recommendation:
        return Recommendation(
            name=item.name,
            url=item.url,
            test_type=item.test_type,
            confidence=confidence,
        )

    def _to_confidence(self, score: int, max_score: int) -> float:
        if max_score <= 0:
            return 0.0
        ratio = score / max_score
        return round(max(0.0, min(1.0, ratio)), 2)

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())
