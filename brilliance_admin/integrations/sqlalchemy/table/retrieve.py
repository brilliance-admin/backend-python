from typing import Any

from brilliance_admin import auth, schema
from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError
from brilliance_admin.integrations.sqlalchemy.fields_schema import SQLAlchemyFieldsSchema
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger

logger = get_logger()


class SQLAlchemyAdminRetrieveMixin:
    has_retrieve: bool = True

    table_schema: SQLAlchemyFieldsSchema

    async def retrieve(
            self,
            pk: Any,
            user: auth.UserABC,
            language_context: LanguageContext,
    ) -> schema.RetrieveResult:
        if not self.has_delete:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

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

        except FieldError as e:
            logger.exception(
                'SQLAlchemy %s retrieve %s #%s field error: %s',
                type(self).__name__, self.model.__name__, pk, e,
            )
            msg = _('errors.serialize_field_error') % {'error': e.message}
            raise AdminAPIException(APIError(message=msg, code='filters_exception'), status_code=500) from e

        except Exception as e:
            logger.exception(
                'SQLAlchemy %s retrieve %s #%s db error: %s',
                type(self).__name__, self.model.__name__, pk, e,
            )
            msg = _('errors.db_error_retrieve') % {'error_type': type(e).__name__}
            raise AdminAPIException(
                APIError(message=msg, code='db_error_retrieve'), status_code=500,
            ) from e

        if record is None:
            msg = _('errors.record_not_found') % {'pk_name': self.pk_name, 'pk': pk}
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
