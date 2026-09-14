from abc import ABC, abstractmethod
from typing import Any

from brilliance_admin.auth import UserABC
from brilliance_admin.schema.table.admin_action import ActionData
from brilliance_admin.utils import get_logger


class HistoryLogsProvider(ABC):
    def __init__(self, category, *, group_slug: str, category_slug: str, subcategory: str | None):
        self.category = category
        self.group_slug = group_slug
        self.category_slug = category_slug
        self.subcategory = subcategory

    @staticmethod
    def get_update_data(before: dict, data: dict) -> dict:
        return {
            field_slug: {'from': before.get(field_slug), 'to': value}
            for field_slug, value in data.items()
            if before.get(field_slug) != value
        }

    @abstractmethod
    async def save_retrieve(self, *, user: UserABC, pk: Any, data: dict, **kwargs) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def save_create(self, *, user: UserABC, pk: Any, data: dict, **kwargs) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def save_update(self, *, user: UserABC, pk: Any, before: dict, data: dict, **kwargs) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def save_admin_action(
            self,
            *,
            user: UserABC,
            action_slug: str,
            action_data: ActionData,
            **kwargs,
    ) -> None:
        raise NotImplementedError()


class HistoryChangeDefaultLogs(HistoryLogsProvider):
    logger = get_logger()

    async def save_retrieve(self, *, user, pk, data, **kwargs) -> None:
        self.logger.debug(
            '%s #%s retrieved by %s',
            type(self.category).__name__, pk, user.username,
            extra={'data': data},
        )

    async def save_create(self, *, user, pk, data, **kwargs) -> None:
        self.logger.info(
            '%s #%s created by %s',
            type(self.category).__name__, pk, user.username,
            extra={'data': data},
        )

    async def save_update(self, *, user, pk, before, data, **kwargs) -> None:
        self.logger.info(
            '%s #%s updated by %s',
            type(self.category).__name__, pk, user.username,
            extra={'data': self.get_update_data(before, data)},
        )

    async def save_admin_action(self, *, user, action_slug, action_data, **kwargs) -> None:
        self.logger.info(
            '%s action %s run by %s',
            type(self.category).__name__, action_slug, user.username,
            extra={'action_data': action_data.model_dump()},
        )
