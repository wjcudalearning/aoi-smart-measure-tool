import json
from pathlib import Path

from aoi_system.core.models.recipe import InspectionRecipe


class RecipeRepository:
    """Manages saving and loading recipes in modern structured JSON format."""

    def __init__(self, storage_dir: Path | str = "recipes"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, recipe: InspectionRecipe) -> Path:
        file_path = self.storage_dir / f"{recipe.product_key}.json"
        data = recipe.model_dump(mode="json")
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return file_path

    def load(self, product_key: str) -> InspectionRecipe | None:
        file_path = self.storage_dir / f"{product_key}.json"
        if not file_path.exists():
            return None
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return InspectionRecipe.model_validate(data)

    def list_all_keys(self) -> list[str]:
        return [p.stem for p in self.storage_dir.glob("*.json")]
