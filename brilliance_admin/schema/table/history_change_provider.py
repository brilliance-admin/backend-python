from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from brilliance_admin.auth import UserABC
from brilliance_admin.schema.table.admin_action import ActionData
from brilliance_admin.schema.table.table_action import TableAction


@dataclass
class HistoryChangeData:
    action: TableAction
    user: UserABC
    group_slug: str
    category_slug: str
    subcategory_slug: str | None = None

    pk: Any | None = None
    data: dict | None = None
    action_slug: str | None = None
    action_data: ActionData | None = None


class HistoryChangeProvider(ABC):
    @abstractmethod
    async def save_action(self, data: HistoryChangeData) -> None:
        raise NotImplementedError()
