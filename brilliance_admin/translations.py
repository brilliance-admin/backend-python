import abc
from importlib import resources
from typing import Any, Dict

import pydantic
from asgiref.local import Local
from pydantic_core import core_schema

from brilliance_admin.utils import DataclassBase, YamlI18n, get_logger

logger = get_logger()

_active = Local()


@pydantic.dataclasses.dataclass
class TranslateText(DataclassBase):
    slug: str
    translation_kwargs: dict | None = None

    def __init__(self, slug: str):
        self.slug = slug

    @pydantic.model_serializer(mode='plain')
    def serialize_model(self, info: pydantic.SerializationInfo) -> str:
        ctx = info.context or {}
        language_context = ctx.get('language_context')

        if not language_context:
            raise AttributeError('language_context is not in context manager for serialization')

        if not issubclass(type(language_context), LanguageContext):
            raise AttributeError(f'language_context "{type(language_context)}" is not subclass of LanguageContext')

        return language_context.get_text(self)

    def __str__(self):
        lm = getattr(_active, '_language_context', None)
        if not lm:

            raise AttributeError(f'language_context is not in local scope for translation: {locals()}')

        if not issubclass(type(lm), LanguageContext):
            raise AttributeError(f'language_context "{lm}" is not subclass of LanguageContext')

        return lm.get_text(self)

    def __mod__(self, other):
        if not isinstance(other, dict):
            msg = f'TranslateText only dict is supported trough % operand (slug="{self.slug}" other={type(other)})'
            raise AttributeError(msg)
        self.translation_kwargs = other
        return self


class LanguageManager(abc.ABC):
    languages: Dict[str, str] | None
    phrases: YamlI18n = None

    def __init__(self, languages: str | None, locales_dir: str | None = None):
        self.languages = languages
        self.phrases = YamlI18n()

        builtin_locales_dir = resources.files("brilliance_admin").joinpath("locales")
        self.phrases.load_folder(builtin_locales_dir)
        logger.debug('Language manager builtin dir loaded: %s', builtin_locales_dir)

        if locales_dir:
            self.phrases.load_folder(locales_dir)
            logger.debug('Language manager locales_dir loaded: %s', locales_dir)

        langs = ', '.join(self.phrases.data.keys())
        logger.debug('Language manager setup completed; languages: %s', langs)

    def get_text(self, text, language) -> str:
        if not isinstance(text, TranslateText):
            return text

        default_lang = list(self.languages.keys())[0]

        translation = self.phrases.get_text(text.slug, language or default_lang, default_lang) or text.slug
        if text.translation_kwargs:
            translation %= text.translation_kwargs

        return translation

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        def validate(v: Any) -> "LanguageManager":
            if isinstance(v, cls):
                return v
            raise TypeError(f"Expected {cls.__name__} instance")

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: repr(v),
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )


class LanguageContext(abc.ABC):
    language: str | None
    language_manager: LanguageManager

    def __init__(self, language, language_manager):
        self.language = language
        self.language_manager = language_manager

        _active._language_context = self

    def get_text(self, text) -> str:
        return self.language_manager.get_text(text, self.language)
