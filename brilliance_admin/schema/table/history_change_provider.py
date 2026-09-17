from abc import ABC, abstractmethod
from enum import Enum
from html import escape
import json
from typing import Any

from fast_diff_match_patch import diff
from pydantic_core import core_schema, to_jsonable_python

from brilliance_admin.auth import UserABC
from brilliance_admin.schema.table.admin_action import ActionData
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger


class LogType(Enum):
    CREATE = 2
    UPDATE = 3
    ADMIN_ACTION = 4

    @property
    def label(self):
        return {
            self.CREATE: _('history.log_type.create'),
            self.UPDATE: _('history.log_type.update'),
            self.ADMIN_ACTION: _('history.log_type.admin_action'),
        }[self]

    @property
    def tag_color(self):
        return {
            self.CREATE: 'green',
            self.UPDATE: 'orange',
            self.ADMIN_ACTION: 'purple',
        }[self]


class HistoryLogsProvider(ABC):
    @staticmethod
    def diff(before: str, after: str) -> tuple[str, str]:
        before_result = []
        after_result = []
        changes = diff(before, after, counts_only=False)

        for operation, text in changes:
            text = escape(text)
            if operation == '=':
                before_result.append(text)
                after_result.append(text)
            elif operation == '-':
                before_result.append(f'<span class="history-diff-removed">{text}</span>')
            elif operation == '+':
                after_result.append(f'<span class="history-diff-added">{text}</span>')
            else:
                raise RuntimeError(f'Unknown diff operation: {operation}')

        return ''.join(before_result), ''.join(after_result)

    @staticmethod
    def serialize_diff_value(value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @classmethod
    def get_update_data(cls, before: dict, data: dict, language_context) -> dict:
        context = {'language_context': language_context}
        before = to_jsonable_python(before, context=context)
        data = to_jsonable_python(data, context=context)
        result = {}
        for field_slug, value in data.items():
            if before.get(field_slug) != value:
                before_value = before.get(field_slug)
                if before_value is not None and value is not None:
                    before_value, value = cls.diff(
                        cls.serialize_diff_value(before_value),
                        cls.serialize_diff_value(value),
                    )
                    result[field_slug] = {'from': before_value, 'to': value, 'html_diff': True}
                else:
                    result[field_slug] = {'from': before_value, 'to': value}
        return result

    @abstractmethod
    async def save_create(
            self, *, category, parent_category, user: UserABC, pk: Any, data: dict, **kwargs,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def save_update(
            self, *, category, parent_category, user: UserABC, pk: Any, before: dict, data: dict, language_context, **kwargs,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def save_admin_action(
            self,
            *,
            category,
            parent_category,
            user: UserABC,
            action_slug: str,
            action_data: ActionData,
            **kwargs,
    ) -> None:
        raise NotImplementedError()

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        def validate(v):
            if not hasattr(v, '__str__'):
                raise TypeError(f'value must implement __str__, got {type(v)}')
            return v

        return core_schema.no_info_plain_validator_function(validate)


class HistoryChangeDefaultLogs(HistoryLogsProvider):
    logger = get_logger()

    async def save_create(self, *, category, parent_category, user, pk, data, **kwargs) -> None:
        self.logger.info(
            '%s #%s created by %s',
            type(category).__name__, pk, user.username,
            extra={'data': data},
        )

    async def save_update(self, *, category, parent_category, user, pk, before, data, language_context, **kwargs) -> None:
        self.logger.info(
            '%s #%s updated by %s',
            type(category).__name__, pk, user.username,
            extra={'data': self.get_update_data(before, data, language_context)},
        )

    async def save_admin_action(self, *, category, parent_category, user, action_slug, action_data, **kwargs) -> None:
        self.logger.info(
            '%s action %s run by %s',
            type(category).__name__, action_slug, user.username,
            extra={'action_data': action_data.model_dump()},
        )
