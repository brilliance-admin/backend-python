from enum import Enum


class SchemaType(str, Enum):
    TABLE = 'table'
    FILTERS = 'filters'
    ACTION = 'action'
