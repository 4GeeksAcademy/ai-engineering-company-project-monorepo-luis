"""Small in-process TTL cache for derived API read responses."""

from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Callable, Generic, Hashable, TypeVar, cast

T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLResponseCache:
    """Cache derived response values until expiry or explicit invalidation."""

    def __init__(self) -> None:
        self._entries: dict[Hashable, _CacheEntry[object]] = {}
        self._lock = RLock()

    def _remove_expired(self, now: float) -> None:
        expired_keys = [
            key for key, entry in self._entries.items() if entry.expires_at <= now
        ]
        for key in expired_keys:
            del self._entries[key]

    def get_or_set(
        self,
        key: Hashable,
        ttl_seconds: float,
        factory: Callable[[], T],
    ) -> T:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")

        with self._lock:
            now = monotonic()
            self._remove_expired(now)
            entry = self._entries.get(key)
            if entry is not None:
                return cast(T, deepcopy(entry.value))

            value = factory()
            self._entries[key] = _CacheEntry(
                value=deepcopy(value),
                expires_at=monotonic() + ttl_seconds,
            )
            return deepcopy(value)

    def invalidate(self, key: Hashable) -> None:
        with self._lock:
            self._remove_expired(monotonic())
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


response_cache = TTLResponseCache()
