from brilliance_admin import auth, schema
from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError
from brilliance_admin.integrations.sqlalchemy.fields_schema import SQLAlchemyFieldsSchema
from brilliance_admin.schema.admin_schema import AdminSchema
from brilliance_admin.translations import LanguageContext
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger

logger = get_logger()


class SQLAlchemyAdminListMixin:
    table_schema: SQLAlchemyFieldsSchema
    table_filters: SQLAlchemyFieldsSchema | None

    def apply_ordering(self, stmt, list_data):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import asc, desc
        from sqlalchemy.orm import InstrumentedAttribute

        ordering = list_data.ordering or self.default_ordering

        if not ordering:
            return stmt

        direction = asc

        if ordering.startswith("-"):
            ordering = ordering[1:]
            direction = desc

        if list_data.ordering and ordering not in self.ordering_fields:
            msg = f'Ordering "{ordering}" is not allowed; available options: {self.ordering_fields} default_ordering: {self.default_ordering}'
            raise FieldError(message=msg, field_slug='ordering')

        column = getattr(self.model, ordering, None)
        if not isinstance(column, InstrumentedAttribute):
            msg = f'{type(self).__name__} ordering field "{ordering}" not found in model {self.model}'
            raise FieldError(message=msg, field_slug='ordering')

        return stmt.order_by(direction(column))

    def apply_search(self, stmt, list_data: schema.ListData):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import String, cast, or_
        from sqlalchemy.orm import InstrumentedAttribute

        if not self.search_fields or not list_data.search:
            return stmt

        search = list_data.search
        conditions = []

        for field_slug in self.search_fields:
            column = getattr(self.model, field_slug, None)
            if not isinstance(column, InstrumentedAttribute):
                msg = f'{type(self).__name__} filter "{field_slug}" not found as field inside model {self.model}'
                raise AttributeError(msg)

            conditions.append(cast(column, String).ilike(search))

        if conditions:
            stmt = stmt.where(or_(*conditions))

        return stmt

    async def apply_filters(self, stmt, list_data: schema.ListData):
        if not self.table_filters or not list_data.filters:
            return stmt

        if not issubclass(type(self.table_filters), SQLAlchemyFieldsSchema):
            msg = f'{type(self).__name__}.table_filters {type(self.table_filters)} must be SQLAlchemyFieldsSchema subclass'
            raise AttributeError(msg)

        return await self.table_filters.apply_filters(stmt, list_data.filters)

    def apply_pagination(self, stmt, list_data: schema.ListData):
        page = max(1, list_data.page or 1)
        limit = min(150, max(1, list_data.limit or 25))

        offset = (page - 1) * limit

        return stmt.limit(limit).offset(offset)

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    async def get_list(
        self,
        list_data: schema.ListData,
        user: auth.UserABC,
        language_context: LanguageContext,
        admin_schema: AdminSchema,
    ) -> schema.TableListResult:
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import exc, func, select

        try:
            stmt = self.get_queryset()
            stmt = await self.apply_filters(stmt, list_data)
            stmt = self.apply_search(stmt, list_data)

            count_stmt = select(func.count()).select_from(stmt.subquery())
            stmt = self.apply_pagination(stmt, list_data)
            stmt = self.apply_ordering(stmt, list_data)

        except FieldError as e:
            logger.exception(
                'SQLAlchemy %s list filters for %s field error: %s',
                type(self).__name__, self.model.__name__, e,
                extra={
                    'list_data': list_data,
                }
            )
            msg = _('errors.filter_error') % {'error': e.message}
            raise AdminAPIException(APIError(message=msg, code='filters_exception'), status_code=500) from e

        except Exception as e:
            logger.exception(
                'SQLAlchemy %s list filters for %s error: %s',
                type(self).__name__, self.model.__name__, e,
                extra={
                    'list_data': list_data,
                }
            )
            msg = _('errors.filters_exception') % {
                'error': str(e) if admin_schema.debug else type(e).__name__,
            }
            raise AdminAPIException(APIError(message=msg, code='filters_exception'), status_code=500) from e

        try:
            async with self.db_async_session() as session:
                total_count = await session.scalar(count_stmt)
                records = (await session.execute(stmt)).scalars().all()

        except ConnectionRefusedError as e:
            logger.exception(
                'SQLAlchemy %s get_list db error: %s',
                type(self).__name__, e,
                extra={
                    'list_data': list_data,
                }
            )
            msg = _('errors.connection_refused_error') % {'error': str(e)}
            raise AdminAPIException(
                APIError(message=msg, code='connection_refused_error'),
                status_code=500,
            ) from e

        except (exc.IntegrityError, exc.StatementError) as e:
            logger.exception(
                'SQLAlchemy %s get_list db error: %s',
                type(self).__name__, e,
                extra={
                    'list_data': list_data,
                }
            )
            orig = e.orig
            message = orig.args[0] if orig.args else type(orig).__name__
            raise AdminAPIException(
                APIError(message=message, code='db_exception'), status_code=500,
            ) from e

        except Exception as e:
            logger.exception(
                'SQLAlchemy %s get_list db error: %s',
                type(self).__name__, e,
                extra={
                    'list_data': list_data,
                }
            )
            msg = _('errors.db_error_list') % {
                'error_type': str(e) if admin_schema.debug else type(e).__name__,
            }
            raise AdminAPIException(
                APIError(message=msg, code='db_error_list'), status_code=500,
            ) from e

        try:
            data = []
            for record in records:
                line = await self.table_schema.serialize(
                    record,
                    extra={"record": record, "user": user},
                )
                data.append(line)

        except FieldError as e:
            logger.exception(
                'SQLAlchemy %s list %s serialize field error: %s',
                type(self).__name__, self.model.__name__, e,
            )
            msg = _('serialize_error.field_error') % {
                'error': e.message,
                'field_slug': e.field_slug,
            }
            raise AdminAPIException(APIError(message=msg, code='field_error'), status_code=500) from e

        except Exception as e:
            logger.exception(
                'SQLAlchemy %s list %s serialize error: %s',
                type(self).__name__, self.model.__name__, e,
            )
            msg = _('serialize_error.unexpected_error') % {
                'error': str(e) if admin_schema.debug else type(e).__name__,
            }
            raise AdminAPIException(APIError(message=msg, code='unexpected_error'), status_code=500) from e

        return schema.TableListResult(data=data, total_count=int(total_count or 0))
