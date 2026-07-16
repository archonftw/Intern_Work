import json
from pathlib import Path
from functools import lru_cache

SCHEMA_DIR = Path(__file__).parent.parent / "schemas"

@lru_cache(maxsize=None)
def load_schema(schema_name: str) -> dict:
    """Load and cache a JSON schema by filename (without .json extension)."""
    schema_path = SCHEMA_DIR / f"{schema_name}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(schema_path, "r") as f:
        return json.load(f)

def reload_schemas():
    """Clear the schema cache — call this if you add a hot-reload endpoint later."""
    load_schema.cache_clear()