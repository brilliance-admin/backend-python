import logging
import re

from pydantic import TypeAdapter


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


class DataclassBase:
    def model_dump(self, *args, **kwargs) -> dict:
        adapter = TypeAdapter(type(self))
        return adapter.dump_python(self, *args, **kwargs)

    def to_dict(self, keep_none=True) -> dict:
        data = self.model_dump()
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
