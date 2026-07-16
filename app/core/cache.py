import threading
from datetime import datetime, timedelta
from typing import Any, Optional

class ShortLivedCache:
    def __init__(self, ttl_seconds: int = 60):
        self._store = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                data, expires_at = self._store[key]
                if datetime.now() > expires_at:
                    del self._store[key]
                    return None
                return data
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            expires_at = datetime.now() + timedelta(seconds=self._ttl)
            self._store[key] = (value, expires_at)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
