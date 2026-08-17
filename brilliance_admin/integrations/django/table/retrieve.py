from asgiref.sync import sync_to_async
from django.db import connections
from django.test.utils import CaptureQueriesContext

from brilliance_admin import schema
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.translations import TranslateText as _


class DjangoAdminRetrieveMixin:
    has_retrieve: bool = True

    @staticmethod
    def get_debug_info_from_context(ctx):
        return schema.DebugInfo(
            db_query_count=len(ctx),
            queries=[
                schema.DebugQuery(
                    sql=query['sql'],
                    time_ms=float(query['time']) * 1000 if query.get('time') else None,
                )
                for query in ctx.captured_queries
            ],
        )

    @staticmethod
    def _load_record_with_debug(queryset):
        connection = connections[queryset.db]
        with CaptureQueriesContext(connection) as ctx:
            record = queryset.first()
        return record, DjangoAdminRetrieveMixin.get_debug_info_from_context(ctx)

    async def retrieve(
        self,
        pk,
        user,
        language_context,
        debug: bool,
        parent_category=None,
        parent_pk=None,
    ) -> schema.RetrieveResult:
        if not self.has_retrieve:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        queryset = self.get_queryset().filter(**{self.pk_name: pk})
        queryset = self.apply_parent_filter(queryset, parent_category, parent_pk)
        debug_info = None
        if debug:
            record, debug_info = await sync_to_async(
                self._load_record_with_debug,
                thread_sensitive=True,
            )(queryset)
        else:
            record = await queryset.afirst()
        if record is None:
            error = APIError(
                message=_('errors.record_not_found') % {'pk_name': self.pk_name, 'pk': pk},
                code='record_not_found',
            )
            raise AdminAPIException(
                error,
                status_code=400,
            )
        data = await self.table_schema.serialize(
            record,
            extra={
                "record": record,
                "user": user,
                "debug": debug,
                "raise_async_unsafe": self.raise_async_unsafe,
            },
        )
        return schema.RetrieveResult(data=data, debug_info=debug_info)
