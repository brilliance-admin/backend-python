from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger

logger = get_logger()


class SQLAlchemyAdminCreate:
    has_create: bool = True

    async def create(
            self,
            data: dict,
            user: UserABC,
            language_context: LanguageContext,
            admin_schema: AdminSchema,
    ) -> schema.CreateResult:
        if not self.has_create:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        # pylint: disable=import-outside-toplevel
        from sqlalchemy.exc import IntegrityError

        try:
            async with self.db_async_session() as session:
                record = await self.table_schema.create(user, data, session)
                pk_value = getattr(record, self.pk_name, None)

        except AdminAPIException as e:
            raise e

        except ConnectionRefusedError as e:
            logger.exception(
                'SQLAlchemy %s create %s db error: %s',
                type(self).__name__, self.table_schema.model.__name__, e,
                extra={'data': data},
            )
            msg = _('errors.connection_refused_error') % {'error': str(e)}
            raise AdminAPIException(
                APIError(message=msg, code='connection_refused_error'),
                status_code=500,
            ) from e

        except IntegrityError as e:
            logger.warning(
                'SQLAlchemy %s create %s db error: %s',
                type(self).__name__, self.table_schema.model.__name__, e,
                extra={'data': data},
            )
            orig = e.orig
            message = orig.args[0] if orig.args else type(orig).__name__
            raise AdminAPIException(
                APIError(message=message, code='db_integrity_error'), status_code=500,
            ) from e

        except Exception as e:
            logger.exception(
                'SQLAlchemy %s create %s db error: %s',
                type(self).__name__, self.table_schema.model.__name__, e,
                extra={'data': data},
            )
            msg = _('errors.db_error_create') % {'error_type': type(e).__name__}
            raise AdminAPIException(
                APIError(message=msg, code='db_error_create'), status_code=500,
            ) from e

        logger.info(
            '%s model %s #%s created by %s',
            type(self).__name__, self.table_schema.model.__name__, pk_value, user.username,
            extra={'data': data},
        )
        return schema.CreateResult(pk=pk_value)
