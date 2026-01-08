from typing import Any

from brilliance_admin.integrations.sqlalchemy.autocomplete import SQLAlchemyAdminAutocompleteMixin
from brilliance_admin.integrations.sqlalchemy.fields_schema import SQLAlchemyFieldsSchema
from brilliance_admin.schema.table.category_table import CategoryTable
from brilliance_admin.translations import TranslateText as _

EXCEPTION_REL_NAME = '''
Model "{model_name}" doesn\'t contain rel_name:"{rel_name}" for field "{slug}"
Model fields = {model_attrs}
'''


class SQLAlchemyAdminBase(SQLAlchemyAdminAutocompleteMixin, CategoryTable):
    model: Any
    slug = None
    ordering_fields = []

    search_fields = []

    table_schema: SQLAlchemyFieldsSchema

    db_async_session: Any = None

    def __init__(
            self,
            *args,
            model=None,
            table_schema=None,
            db_async_session=None,
            ordering_fields=None,
            default_ordering=None,
            search_fields=None,
            **kwargs,
    ):
        if model:
            self.model = model

        if search_fields:
            self.search_fields = search_fields

        if self.search_fields:
            self.search_enabled = True
            self.search_help = _('sqlalchemy_search_help') % {'fields': ', '.join(self.search_fields)}

        if default_ordering:
            self.default_ordering = default_ordering

        if ordering_fields:
            self.ordering_fields = ordering_fields

        self.validate_fields()

        if table_schema:
            self.table_schema = table_schema

        if not self.table_schema:
            self.table_schema = SQLAlchemyFieldsSchema(model=self.model)

        if not issubclass(type(self.table_schema), SQLAlchemyFieldsSchema):
            msg = f'{type(self).__name__}.table_schema {self.table_schema} must be subclass of SQLAlchemyFieldsSchema'
            raise AttributeError(msg)

        if not self.model:
            msg = f'{type(self).__name__}.model is required for SQLAlchemy'
            raise AttributeError(msg)

        if not self.slug:
            self.slug = self.model.__name__.lower()

        if db_async_session:
            self.db_async_session = db_async_session

        if not self.db_async_session:
            msg = f'{type(self).__name__}.db_async_session is required for SQLAlchemy'
            raise AttributeError(msg)

        # pylint: disable=import-outside-toplevel
        from sqlalchemy import inspect
        from sqlalchemy.sql.schema import Column

        for attr in inspect(self.model).mapper.column_attrs:
            col: Column = attr.columns[0]
            if col.primary_key and not self.pk_name:
                self.pk_name = attr.key
                break

        if not self.default_ordering and self.pk_name:
            self.default_ordering = f'-{self.pk_name}'

        super().__init__(*args, **kwargs)

    def validate_fields(self):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy.orm import InstrumentedAttribute

        if self.search_fields:
            for field in self.search_fields:
                column = getattr(self.model, field, None)
                if not isinstance(column, InstrumentedAttribute):
                    raise AttributeError(
                        f'{type(self).__name__}: search field "{field}" not found in model {self.model.__name__}'
                    )

        if self.ordering_fields:
            for field in self.ordering_fields:
                column = getattr(self.model, field, None)
                if not isinstance(column, InstrumentedAttribute):
                    raise AttributeError(
                        f'{type(self).__name__}: ordering field "{field}" not found in model {self.model.__name__}'
                    )

    def get_queryset(self):
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = select(self.model).options(selectinload('*'))

        # Eager-load related fields
        for slug, field in self.table_schema.get_fields().items():

            # pylint: disable=protected-access
            if field._type == "related":

                if not hasattr(self.model, field.rel_name):
                    # pylint: disable=import-outside-toplevel
                    from sqlalchemy import inspect
                    model_attrs = [attr.key for attr in inspect(self.model).mapper.attrs]

                    msg = EXCEPTION_REL_NAME.format(
                        slug=slug,
                        model_name=self.model.__name__,
                        rel_name=field.rel_name,
                        model_attrs=model_attrs,
                    )
                    raise AttributeError(msg)

                stmt = stmt.options(selectinload(getattr(self.model, field.rel_name)))

        return stmt
