from asgiref.sync import sync_to_async

from brilliance_admin.schema.table.history_change_provider import HistoryChangeDefaultLogs


class DjangoLogsProvider(HistoryChangeDefaultLogs):
    def get_category_path(self) -> str:
        return '/'.join(filter(None, [self.group_slug, self.category.slug, self.subcategory]))

    async def get_content_type(self):
        from django.contrib.contenttypes.models import ContentType

        model = getattr(self.category.table_schema, 'model', None)
        if model is None:
            raise TypeError(
                f'{type(self).__name__} requires category.table_schema.model; '
                f'got {type(self.category.table_schema).__name__}'
            )
        return await sync_to_async(ContentType.objects.get_for_model, thread_sensitive=True)(model)

    async def save_retrieve(self, *, user, pk, data, **kwargs) -> None:
        await super().save_retrieve(user=user, pk=pk, data=data, **kwargs)
        from .models import LogType

        await self.save_record_change(LogType.RETRIEVE, user=user, pk=pk, data=data)

    async def save_create(self, *, user, pk, data, **kwargs) -> None:
        await super().save_create(user=user, pk=pk, data=data, **kwargs)
        from .models import LogType

        await self.save_record_change(LogType.CREATE, user=user, pk=pk, data=data)

    async def save_update(self, *, user, pk, before, data, **kwargs) -> None:
        await super().save_update(user=user, pk=pk, before=before, data=data, **kwargs)
        from .models import LogType

        await self.save_record_change(
            LogType.UPDATE,
            user=user,
            pk=pk,
            data=self.get_update_data(before, data),
        )

    async def save_record_change(self, log_type, *, user, pk, data: dict) -> None:
        from .models import HistoryChange

        await HistoryChange.objects.acreate(
            user=user,
            content_type=await self.get_content_type(),
            object_id=str(pk),
            log_type=log_type.value,
            category_path=self.get_category_path(),
            data=data,
        )

    async def save_admin_action(self, *, user, action_slug, action_data, **kwargs) -> None:
        await super().save_admin_action(
            user=user,
            action_slug=action_slug,
            action_data=action_data,
            **kwargs,
        )
        from .models import HistoryChange, LogType

        await HistoryChange.objects.acreate(
            user=user,
            content_type=await self.get_content_type(),
            log_type=LogType.ADMIN_ACTION.value,
            action_slug=action_slug,
            category_path=self.get_category_path(),
            data=action_data.model_dump(mode='json'),
        )
