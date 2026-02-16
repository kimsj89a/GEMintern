"""
Local storage for settings persistence.
Replaced browser localStorage bridge with JSON file-based storage.
"""

import os
import json

_STORAGE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".local_storage.json"
)


def _load_all():
    try:
        if os.path.exists(_STORAGE_FILE):
            with open(_STORAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_all(data):
    try:
        with open(_STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def local_storage_get(storage_key, default="", st_key=None):
    """Read a value from local storage file."""
    data = _load_all()
    return data.get(storage_key, default)


def local_storage_set(storage_key, value, st_key=None):
    """Write a value to local storage file."""
    data = _load_all()
    data[storage_key] = value
    _save_all(data)
