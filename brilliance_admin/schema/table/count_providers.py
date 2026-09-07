from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import ceil
from typing import Any

@dataclass
class CountResult:
    total_count: str | None
    pages_count: int | None

    @classmethod
    def get_pages_count(cls, total_count: int, limit: int) -> int:
        limit = min(150, max(1, limit))
        return max(1, ceil(total_count / limit))


class CountProvider(ABC):
    @abstractmethod
    async def get_count(self, query: Any, *, category: Any, has_filters: bool, limit: int) -> CountResult:
        pass
