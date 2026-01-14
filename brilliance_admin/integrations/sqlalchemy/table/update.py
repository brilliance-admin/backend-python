from typing import Any

from brilliance_admin import auth, schema
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger

logger = get_logger()


class SQLAlchemyAdminUpdate:
    has_update: bool = True

    # pylint: disable=too-many-locals
    async def update(
            self,
            pk: Any,
            data: dict,
            user: auth.UserABC,
            language_context: LanguageContext,
            admin_schema: AdminSchema,
    ) -> schema.UpdateResult:
        if not self.has_update:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect
        from sqlalchemy.exc import IntegrityError

        if pk is None:
            raise AdminAPIException(
                APIError(message=_('errors.pk_not_found') % {'pk_name': self.pk_name}, code='pk_not_found'),
                status_code=400,
            )

        col = inspect(self.table_schema.model).mapper.columns[self.pk_name]
        python_type = col.type.python_type

        stmt = self.get_queryset().where(getattr(self.model, self.pk_name) == python_type(pk))

        try:
            async with self.db_async_session() as session:
                record = (await session.execute(stmt)).scalars().first()
                if record is None:
                    msg = _('errors.record_not_found') % {'pk_name': self.pk_name, 'pk': pk}
                    raise AdminAPIException(
                        APIError(message=msg, code='record_not_found'),
                        status_code=400,
                    )

                await self.table_schema.update(record, user, data, session)

        except AdminAPIException as e:
            raise e

        except ConnectionRefusedError as e:
            logger.exception(
                'SQLAlchemy %s update %s #%s db connection error: %s',
                type(self).__name__, self.table_schema.model.__name__, pk, e,
                extra={'data': data},
            )
            msg = _('errors.connection_refused_error') % {'error': str(e)}
            raise AdminAPIException(
                APIError(message=msg, code='connection_refused_error'),
                status_code=400,
            ) from e

        except IntegrityError as e:
            logger.warning(
                'SQLAlchemy %s update %s #%s db error: %s',
                type(self).__name__, self.table_schema.model.__name__, pk, e,
                extra={'data': data},
            )
            orig = e.orig
            message = orig.args[0] if orig.args else type(orig).__name__
            raise AdminAPIException(
                APIError(message=message, code='db_integrity_error'), status_code=500,
            ) from e

        except Exception as e:
            logger.exception(
                'SQLAlchemy %s update %s #%s db error: %s',
                type(self).__name__, self.table_schema.model.__name__, pk, e,
                extra={'data': data}
            )
            msg = _('errors.db_error_update') % {'error_type': type(e).__name__}
            raise AdminAPIException(
                APIError(message=msg, code='db_error_update'), status_code=500,
            ) from e

        logger.info(
            '%s model %s #%s updated by %s',
            type(self).__name__, self.table_schema.model.__name__, pk, user.username,
            extra={'data': data},
        )
        return schema.UpdateResult(pk=pk)
