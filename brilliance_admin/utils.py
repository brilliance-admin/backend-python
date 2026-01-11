import logging
import re
from pathlib import Path
from typing import Any, Dict, Protocol

import yaml
from pydantic import TypeAdapter
from pydantic.fields import FieldInfo
from pydantic_core import core_schema


class SupportsStr(Protocol):
    def __str__(self) -> str: ...

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        def validate(v):
            if not hasattr(v, '__str__'):
                raise TypeError(f'value must implement __str__, got {type(v)}')
            return v

        return core_schema.no_info_plain_validator_function(validate)


def get_logger():
    try:
        # pylint: disable=import-outside-toplevel
        import structlog
        return structlog.get_logger('brilliance_admin')
    except ImportError:
        return logging.getLogger('brilliance_admin')


class DeserializeAction:
    CREATE = 0
    UPDATE = 1
    TABLE_ACTION = 2
    FILTERS = 3


class KwargsInitMixin:
    """
    Принимает только аргументы, объявленные в аннотациях.
    Применяет default / default_factory из Field.
    """

    def __init__(self, **kwargs):
        annotations = {}
        for cls in type(self).__mro__:
            annotations.update(getattr(cls, '__annotations__', {}))

        allowed = set(annotations.keys())

        for key, value in kwargs.items():
            if key not in allowed:
                raise AttributeError(
                    f'{type(self).__name__} has no field "{key}". '
                    f'Allowed fields: {sorted(allowed)}'
                )
            setattr(self, key, value)

        self._apply_field_defaults()

    def _apply_field_defaults(self):
        for cls in type(self).__mro__:
            for name, value in cls.__dict__.items():
                if not isinstance(value, FieldInfo):
                    continue

                # если в инстансе всё ещё FieldInfo — заменить
                if getattr(self, name, None) is value:
                    if value.default_factory is not None:
                        setattr(self, name, value.default_factory())
                    elif value.default is not None:
                        setattr(self, name, value.default)


class DataclassBase:
    def model_dump(self, *args, **kwargs) -> dict:
        adapter = TypeAdapter(type(self))
        return adapter.dump_python(self, *args, **kwargs)

    def to_dict(self, *args, keep_none=True, **kwargs) -> dict:
        data = self.model_dump(*args, **kwargs)
        return {
            k: v for k, v in data.items()
            if v is not None and not keep_none
        }


def humanize_field_name(name: str) -> str:
    # Convert snake_case / kebab-case / mixed tokens to Title Case with acronyms preserved
    s = name.replace("-", "_")
    parts = [p for p in s.split("_") if p]

    def cap(token: str) -> str:
        # Keep common acronyms uppercase
        if token.lower() in {"id", "ip", "url", "api", "http", "https", "h2h"}:
            return token.upper()
        # If token contains digits, capitalize first letter only (e.g. "h2h" -> "H2h")
        if re.search(r"\d", token):
            return token[:1].upper() + token[1:].lower()
        return token[:1].upper() + token[1:].lower()

    return " ".join(cap(p) for p in parts)


def iter_locale_files(directory) -> list[Path]:
    if isinstance(directory, str):
        directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(directory)
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    for path in directory.rglob('*'):
        if not path.is_file():
            continue

        yield path


def merge_dict_data(base: dict, extra: dict) -> dict:
    if not isinstance(base, dict):
        raise TypeError('base must be dict')
    if not isinstance(extra, dict):
        raise TypeError('extra must be dict')

    result = base.copy()
    for key, value in extra.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dict_data(result[key], value)
        else:
            result[key] = value
    return result


class YamlI18n:
    data: Dict[str, Any] = {}

    def load_folder(self, path):
        for file_path in iter_locale_files(path):
            with file_path.open(encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                msg = f'YAML root must be dict: {file_path}, got {type(data)}'
                raise TypeError(msg)

            language = file_path.stem
            if language not in self.data:
                self.data[language] = {}

            if not isinstance(self.data[language], dict):
                raise TypeError(f'language root must be dict: {language}')

            self.data[language] = merge_dict_data(self.data[language], data)

    def get_text(self, slug, language, default_language):
        if not isinstance(slug, str):
            raise TypeError(f'slug must be str, got {type(slug)}')

        if not isinstance(language, str):
            raise TypeError(f'language must be str, got {type(language)}')

        if not isinstance(default_language, str):
            raise TypeError(f'default_language must be str, got {type(default_language)}')

        if not self.data:
            raise ValueError('i18n data is empty')

        for lang in (language, default_language):
            if lang not in self.data:
                continue

            node = self.data[lang]

            for part in slug.split('.'):
                if not isinstance(node, dict):
                    node = None
                    break
                if part not in node:
                    node = None
                    break
                node = node[part]

            if isinstance(node, str):
                return node

        return slug
