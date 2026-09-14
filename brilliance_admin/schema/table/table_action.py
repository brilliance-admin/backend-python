from enum import Enum


class TableAction(str, Enum):
    LIST = 'list'
    RETRIEVE = 'retrieve'
    CREATE = 'create'
    UPDATE = 'update'
    ADMIN_ACTION = 'admin_action'
