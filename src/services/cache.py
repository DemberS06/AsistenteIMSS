# services/cache.py

import json
import os
from pathlib import Path
from typing import Optional, Any

from config import CACHE_FILE


def load_cache() -> dict:
    try:
        if not Path(CACHE_FILE).exists():
            return {}
        
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(data: dict) -> None:
    try:
        # Asegurar que el directorio existe
        Path(CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
        
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def load_preference(key: str) -> Optional[Any]:
    cache = load_cache()
    return cache.get(key)


def save_preference(key: str, value: Any) -> None:
    cache = load_cache()
    cache[key] = value
    save_cache(cache)


def delete_preference(key: str) -> None:
    cache = load_cache()
    if key in cache:
        del cache[key]
        save_cache(cache)


def clear_cache() -> None:
    try:
        if Path(CACHE_FILE).exists():
            Path(CACHE_FILE).unlink()
    except Exception:
        pass