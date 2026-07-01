import json
import re
from pathlib import Path
from typing import List, Optional

from app.schemas import Recommendation


DATA_FILE = Path(__file__).resolve().parent / "catalog.json"


class Catalog:
    def __init__(self, data_file: Optional[Path] = None) -> None:
        self.data_file = data_file or DATA_FILE
        self.items = self._load_catalog()

    def _load_catalog(self) -> List[dict]:
        if not self.data_file.exists():
            return self._seed_catalog()
        with self.data_file.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _seed_catalog(self) -> List[dict]:
        seed = [
            {
                "name": "SHL Cognitive Ability Test",
                "url": "https://www.shl.com/en/cognitive-ability-test",
                "test_type": "cognitive",
                "description": "A cognitive assessment for measuring reasoning and problem-solving aptitude.",
                "duration": 45,
                "job_levels": ["mid", "senior"],
                "languages": ["English"],
                "remote_testing": True,
                "adaptive_irt": True,
            },
            {
                "name": "SHL Numerical Reasoning Test",
                "url": "https://www.shl.com/en/numerical-reasoning-test",
                "test_type": "cognitive",
                "description": "A numeracy-focused assessment ideal for analytical and finance roles.",
                "duration": 25,
                "job_levels": ["entry", "mid"],
                "languages": ["English"],
                "remote_testing": True,
                "adaptive_irt": False,
            },
            {
                "name": "SHL Verbal Reasoning Test",
                "url": "https://www.shl.com/en/verbal-reasoning-test",
                "test_type": "cognitive",
                "description": "Assesses language comprehension and written information evaluation.",
                "duration": 20,
                "job_levels": ["entry", "mid", "senior"],
                "languages": ["English"],
                "remote_testing": True,
                "adaptive_irt": False,
            },
            {
                "name": "SHL Personality Questionnaire",
                "url": "https://www.shl.com/en/personality-questionnaire",
                "test_type": "personality",
                "description": "Measures workplace personality traits for role fit and team compatibility.",
                "duration": 20,
                "job_levels": ["mid", "senior"],
                "languages": ["English"],
                "remote_testing": True,
                "adaptive_irt": False,
            },
            {
                "name": "SHL Java Programming Test",
                "url": "https://www.shl.com/en/java-programming-test",
                "test_type": "skills",
                "description": "A practical Java coding assessment for software engineering candidates.",
                "duration": 60,
                "job_levels": ["mid", "senior"],
                "languages": ["English"],
                "remote_testing": True,
                "adaptive_irt": False,
            },
        ]
        self.data_file.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return seed

    def search(self, query: str) -> List[Recommendation]:
        query_terms = [term for term in re.split(r"[^a-z0-9]+", query.lower()) if term]
        if not query_terms:
            return []

        scored = []
        for item in self.items:
            haystack = " ".join(
                [
                    item.get("name", ""),
                    item.get("description", ""),
                    item.get("test_type", ""),
                    " ".join(item.get("job_levels", [])),
                    " ".join(item.get("languages", [])),
                ]
            ).lower()

            score = sum(1 for term in query_terms if term in haystack)
            if score:
                scored.append((score, item))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        return [
            Recommendation(
                name=item["name"],
                url=item["url"],
                test_type=item["test_type"],
                description=item["description"],
            )
            for _, item in scored[:3]
        ]
