from brilliance_admin import schema
from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.integrations.sqlalchemy.utils import extract_integrity_detail
from brilliance_admin.integrations.sqlalchemy.related_field import get_record_title
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger
from brilliance_admin.schema.table.table_models import Record

logger = get_logger()


class SQLAlchemyAdminCreate:
    has_create: bool = True

    def apply_parent_data(self, data: dict, parent_category=None, parent_pk=None) -> dict:
        if parent_category is None or parent_pk is None:
            return data

        fk_field_name = self.get_parent_fk_field_name(parent_category)
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect

        fk_column = inspect(self.model).mapper.columns[fk_field_name]
        python_type = fk_column.type.python_type

        result = dict(data)
        result[fk_field_name] = python_type(parent_pk)
        return result

    async def create(
            self,
            data: dict,
            user: UserABC,
            language_context: LanguageContext,
            debug: bool,
            parent_category=None,
            parent_pk=None,
    ) -> schema.CreateResult:
        if not self.has_create:
            raise AdminAPIException(APIError(message=_('errors.method_not_allowed')), status_code=500)

        data = self.apply_parent_data(data, parent_category, parent_pk)

        # pylint: disable=import-outside-toplevel
        from sqlalchemy.exc import IntegrityError

        try:
            async with self.db_async_session() as session:
                record = await self.table_schema.create(user, data, session)
                pk_value = getattr(record, self.pk_name, None)
                choice = Record(
                    key=pk_value,
                    title=get_record_title(record, self.raise_async_unsafe, debug=debug),
                )

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
            detail = extract_integrity_detail(e)
            raise AdminAPIException(
                APIError(
                    message=_('errors.db_integrity_error') % {'detail': detail},
                    code='db_integrity_error',
                ), status_code=500,
            ) from e

        except Exception as e:
            logger.exception(
                'SQLAlchemy %s create %s db error: %s',
                type(self).__name__, self.table_schema.model.__name__, e,
                extra={'data': data},
            )
            msg = _('errors.db_error_create') % {
                'error_type': str(e) if debug else type(e).__name__,
            }
            raise AdminAPIException(
                APIError(message=msg, code='db_error_create'), status_code=500,
            ) from e

        logger.info(
            '%s model %s #%s created by %s',
            type(self).__name__, self.table_schema.model.__name__, pk_value, user.username,
            extra={'data': data},
        )
        return schema.CreateResult(pk=pk_value, choice=choice)
