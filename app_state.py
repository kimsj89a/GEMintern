"""
Global application state management - replaces st.session_state.
Uses Qt signals to notify widgets of state changes.
"""

from PyQt6.QtCore import QObject, pyqtSignal


class AppState(QObject):
    """Singleton state manager with change notification signals."""

    state_changed = pyqtSignal(str, object)  # key, value
    _instance = None
    _data: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
            cls._data = {}
        return cls._instance

    @classmethod
    def get(cls, key, default=None):
        return cls._data.get(key, default)

    @classmethod
    def set(cls, key, value):
        cls._data[key] = value
        inst = cls()
        inst.state_changed.emit(key, value)

    @classmethod
    def setdefault(cls, key, default):
        if key not in cls._data:
            cls._data[key] = default
        return cls._data[key]

    @classmethod
    def pop(cls, key, default=None):
        return cls._data.pop(key, default)

    @classmethod
    def has(cls, key):
        return key in cls._data

    @classmethod
    def keys(cls):
        return cls._data.keys()

    @classmethod
    def clear_prefix(cls, prefix):
        """Clear all keys starting with prefix."""
        to_del = [k for k in cls._data if k.startswith(prefix)]
        for k in to_del:
            del cls._data[k]

    @classmethod
    def items(cls):
        return cls._data.items()
