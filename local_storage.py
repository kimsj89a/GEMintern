"""
Browser localStorage bridge for Streamlit.
Allows reading/writing values to the user's browser localStorage,
persisting data across sessions even on Streamlit Cloud.
"""

import os
import streamlit.components.v1 as components

_COMP_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "components", "local_storage"
)
_local_storage_func = components.declare_component("local_storage", path=_COMP_DIR)


def local_storage_get(storage_key, default="", st_key=None):
    """Read a value from browser localStorage.
    Returns the stored value, or default if not found.
    Note: Returns default on the first render; actual value arrives on rerun.
    """
    result = _local_storage_func(
        storage_key=storage_key,
        default=default,
        key=st_key,
    )
    return result if result else default


def local_storage_set(storage_key, value, st_key=None):
    """Write a value to browser localStorage."""
    _local_storage_func(
        storage_key=storage_key,
        save_value=value,
        default=value,
        key=st_key,
    )
