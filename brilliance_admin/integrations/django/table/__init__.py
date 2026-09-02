from .base import DjangoAdminBase
from .count_providers import DjangoCountProvider, PostgresCounter
from .create import DjangoAdminCreate
from .delete import DjangoDeleteAction
from .export import DjangoPostgresExportAction
from .list import DjangoAdminListMixin
from .retrieve import DjangoAdminRetrieveMixin
from .update import DjangoAdminUpdate


class DjangoAdmin(
    DjangoAdminUpdate,
    DjangoAdminCreate,
    DjangoDeleteAction,
    DjangoAdminListMixin,
    DjangoAdminRetrieveMixin,
    DjangoAdminBase,
):
    pass
