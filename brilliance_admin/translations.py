import abc
from typing import ClassVar, Dict

import pydantic
from asgiref.local import Local

from brilliance_admin.utils import DataclassBase

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
        language_manager = ctx.get('language_manager')

        if not language_manager:
            raise AttributeError('language_manager is not in context manager for serialization')

        if not issubclass(type(language_manager), LanguageManager):
            raise AttributeError(f'language_manager "{type(language_manager)}" is not subclass of LanguageManager')

        return language_manager.get_text(self)

    def __str__(self):
        lm = getattr(_active, '_language_manager', None)
        if not lm:

            raise AttributeError(f'language_manager is not in local scope for translation: {locals()}')

        if not issubclass(type(lm), LanguageManager):
            raise AttributeError(f'language_manager "{lm}" is not subclass of LanguageManager')

        return lm.get_text(self)

    def __mod__(self, other):
        if not isinstance(other, dict):
            msg = f'TranslateText only dict is supported trough % operand (slug="{self.slug}" other={type(other)})'
            raise AttributeError(msg)
        self.translation_kwargs = other
        return self


SQLALCHEMY_SEARCH_HELP_RU = '''<b>Доступные поля для поиска:</b>
%(fields)s

<b>Доступные операторы:</b>
<b>""</b> - кавычки для точного совпадения
<b>%%</b> - любая последовательность символов
<b>_</b> - один любой символ
'''
sqlalchemy_search_help_EN = '''<b>Available search fields:</b>
%(fields)s

<b>Available operators:</b>
<b>""</b> - quotes for exact match
<b>%%</b> - any sequence of characters
<b>_</b> - any single character
'''

DEFAULT_PHRASES = {
    'ru': {
        'delete': 'Удалить',
        'delete_confirmation_text': 'Вы уверены, что хотите удалить данные записи?\nДанное действие нельзя отменить.',
        'deleted_successfully': 'Записи успешно удалены.',
        'pk_not_found': 'Поле "%(pk_name)s" не найдено среди переданных данных.',
        'record_not_found': 'Запись по ключу %(pk_name)s=%(pk)s не найдена.',
        'db_error_create': 'Ошибка создания записи в базе данных.',
        'db_error_update': 'Ошибка обновления записи в базе данных.',
        'db_error_retrieve': 'Ошибка получения записи из базы данных.',
        'db_error_list': 'Ошибка получения данных таблицы из базы данных.',
        'connection_refused_error': 'Ошибка подключения к базе данных: %(error)s',
        'search_help': 'Доступные поля для поиска: %(fields)s',
        'sqlalchemy_search_help': SQLALCHEMY_SEARCH_HELP_RU,
        'filters_exception': 'Произошла неизвестная техническая ошибка при фильтрации данных.',
        'method_not_allowed': 'Ошибка, данный метод недоступен.',
        'filter_error': 'Проишла ошибка при фильтрации: {error}',
    },
    'en': {
        'delete': 'Delete',
        'delete_confirmation_text': 'Are you sure you want to delete those records?\nThis action cannot be undone.',
        'deleted_successfully': 'The entries were successfully deleted.',
        'pk_not_found': 'The "%(pk_name)s" field was not found in the submitted data.',
        'record_not_found': 'No record found for %(pk_name)s=%(pk)s.',
        'db_error_update': 'Error updating the record in the database.',
        'db_error_create': 'Error creating a record in the database.',
        'db_error_retrieve': 'Error retrieving the record from the database.',
        'db_error_list': 'Failed to retrieve table data from the database.',
        'connection_refused_error': 'Database connection error: %(error)s',
        'search_help': 'Available search fields: %(fields)s',
        'sqlalchemy_search_help': sqlalchemy_search_help_EN,
        'filters_exception': 'An unknown technical error occurred while filtering data.',
        'method_not_allowed': 'Error, method not allowed. This action is not permitted.',
        'filter_error': 'An error occurred during filtering: {error}',
    }
}


def merge_phrases(base: dict[str, dict[str, str]], extra: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    merged = {lang: phrases.copy() for lang, phrases in base.items()}

    for lang, phrases in extra.items():
        if lang in merged:
            merged[lang].update(phrases)

    return merged


class LanguageManager(abc.ABC):
    language: str | None

    languages: ClassVar[Dict[str, str | TranslateText] | None] = None
    languages_phrases: ClassVar[dict | None] = None

    def __init__(self, language: str | None):
        self.language = language
        _active._language_manager = self

        if not self.languages_phrases:
            self.languages_phrases = {}

        self.languages_phrases = merge_phrases(self.languages_phrases, DEFAULT_PHRASES)

    def get_text(self, text) -> str:
        if self.languages_phrases and isinstance(text, TranslateText):
            default_lang = list(self.languages_phrases.keys())[0]

            phrases = self.languages_phrases.get(self.language or default_lang)
            if not phrases:
                phrases = self.languages_phrases[default_lang]

            translation = phrases.get(text.slug) or text.slug
            if text.translation_kwargs:
                translation %= text.translation_kwargs
            return translation

        return text
