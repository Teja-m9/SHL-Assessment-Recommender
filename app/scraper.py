import json
from pathlib import Path
from typing import Any, Optional


class CatalogScraper:
    """
    Imports a prepared SHL catalog export into the app catalog format.

    This keeps the runtime app offline-friendly while allowing the repository
    to ingest a full catalog snapshot when one is available.
    """

    def __init__(self, source_path: Path, output_path: Optional[Path] = None) -> None:
        self.source_path = source_path
        self.output_path = output_path or Path(__file__).resolve().parent / "catalog.json"

    def scrape(self) -> list[dict[str, Any]]:
        with self.source_path.open("r", encoding="utf-8") as handle:
            raw_items = json.load(handle)

        normalized = [self._normalize_item(item) for item in raw_items]
        self.output_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
        return normalized

    def _normalize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": item["name"],
            "url": item["url"],
            "test_type": item["test_type"],
            "description": item.get("description", ""),
            "job_levels": item.get("job_levels", []),
            "keywords": item.get("keywords", []),
            "roles": item.get("roles", []),
            "skills": item.get("skills", []),
        }
