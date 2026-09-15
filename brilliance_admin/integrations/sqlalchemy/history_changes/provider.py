from typing import Any

from brilliance_admin.schema.table.history_change_provider import HistoryChangeDefaultLogs

from .models import HistoryChange, LogType


class SQLAlchemyLogsProvider(HistoryChangeDefaultLogs):
    db_async_session = None

    def __init__(self, db_async_session):
        self.db_async_session = db_async_session

    def get_category_path(self, category, parent_category) -> str:
        group_slug = category._group_slug
        if group_slug is None:
            raise ValueError(f'{type(category).__name__} is not included in a CategoryGroup')

        path = [group_slug]
        if parent_category is not None:
            path.append(parent_category.slug)
        path.append(category.slug)
        return '/'.join(path)

    async def save_record_change(
            self,
            log_type: LogType,
            *,
            category,
            parent_category,
            user,
            pk: Any | None = None,
            data: dict,
            action_slug: str | None = None,
    ) -> None:
        record = HistoryChange(
            user=user.username,
            pk=None if pk is None else str(pk),
            log_type=log_type.value,
            action_slug=action_slug,
            category_path=self.get_category_path(category, parent_category),
            data=data,
        )
        async with self.db_async_session() as session:
            session.add(record)
            await session.commit()

    async def save_create(self, *, category, parent_category, user, pk, data, **kwargs) -> None:
        await super().save_create(
            category=category, parent_category=parent_category, user=user, pk=pk, data=data, **kwargs,
        )
        await self.save_record_change(
            LogType.CREATE, category=category, parent_category=parent_category, user=user, pk=pk, data=data,
        )

    async def save_update(self, *, category, parent_category, user, pk, before, data, **kwargs) -> None:
        await super().save_update(
            category=category, parent_category=parent_category,
            user=user, pk=pk, before=before, data=data, **kwargs,
        )
        await self.save_record_change(
            LogType.UPDATE,
            category=category,
            parent_category=parent_category,
            user=user,
            pk=pk,
            data=self.get_update_data(before, data),
        )

    async def save_admin_action(self, *, category, parent_category, user, action_slug, action_data, **kwargs) -> None:
        await super().save_admin_action(
            category=category,
            parent_category=parent_category,
            user=user,
            action_slug=action_slug,
            action_data=action_data,
            **kwargs,
        )
        await self.save_record_change(
            LogType.ADMIN_ACTION,
            category=category,
            parent_category=parent_category,
            user=user,
            action_slug=action_slug,
            data=action_data.model_dump(mode='json'),
        )
