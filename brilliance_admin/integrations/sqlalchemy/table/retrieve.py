from typing import Any

from brilliance_admin import auth, schema
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.translations import LanguageManager
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger

logger = get_logger()


class SQLAlchemyAdminRetrieveMixin:
    has_retrieve: bool = True

    async def retrieve(
            self,
            pk: Any,
            user: auth.UserABC,
            language_manager: LanguageManager,
    ) -> schema.RetrieveResult:
        if not self.has_delete:
            raise AdminAPIException(APIError(message=_('method_not_allowed')), status_code=500)

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        col = inspect(self.model).mapper.columns[self.pk_name]
        python_type = col.type.python_type

        assert self.pk_name
        stmt = self.get_queryset().where(getattr(self.model, self.pk_name) == python_type(pk))

        try:
            async with self.db_async_session() as session:
                record = (await session.execute(stmt)).scalars().first()
                data = await self.table_schema.serialize(
                    record,
                    extra={"record": record, "user": user},
                )

        except Exception as e:
            logger.exception(
                'SQLAlchemy %s retrieve db error: %s', type(self).__name__, e,
            )
            raise AdminAPIException(
                APIError(message=_('db_error_retrieve'), code='db_error_retrieve'), status_code=500,
            ) from e

        if record is None:
            msg = _('record_not_found') % {'pk_name': self.pk_name, 'pk': pk}
            raise AdminAPIException(
                APIError(message=msg, code='record_not_found'),
                status_code=400,
            )

        logger.debug(
            '%s model %s #%s retrieved by %s',
            type(self).__name__, self.table_schema.model.__name__, pk, user.username,
            extra={'data': data},
        )
        return schema.RetrieveResult(data=data)
