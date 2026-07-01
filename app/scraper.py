import json
from pathlib import Path
from typing import List, Optional


class CatalogScraper:
    """Small scraper placeholder that can be swapped for a real implementation later."""

    def __init__(self, output_path: Optional[Path] = None) -> None:
        self.output_path = output_path or Path(__file__).resolve().parent / "catalog.json"

    def scrape(self) -> List[dict]:
        # In a real implementation this would fetch and parse SHL catalog pages.
        # For now it simply preserves the seed catalog shape.
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
        self.output_path.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return seed
