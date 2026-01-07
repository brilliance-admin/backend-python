# pylint: disable=wildcard-import, unused-wildcard-import, unused-import, too-many-ancestors
# flake8: noqa: F405
from .base import SQLAlchemyAdminBase
from .create import SQLAlchemyAdminCreate
from .delete import SQLAlchemyDeleteAction
from .list import SQLAlchemyAdminListMixin
from .retrieve import SQLAlchemyAdminRetrieveMixin
from .update import SQLAlchemyAdminUpdate


class SQLAlchemyAdmin(
        SQLAlchemyAdminUpdate,
        SQLAlchemyAdminCreate,
        SQLAlchemyDeleteAction,
        SQLAlchemyAdminListMixin,
        SQLAlchemyAdminRetrieveMixin,
        SQLAlchemyAdminBase,
):
    pass
