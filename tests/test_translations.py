import pytest

from admin_panel.exceptions import AdminAPIException, APIError, FieldError
from admin_panel.translations import DEFAULT_PHRASES
from admin_panel.translations import TranslateText as _
from admin_panel.translations import merge_phrases
from example.main import CustomLanguageManager


@pytest.mark.asyncio
async def test_translate_exception(mocker):
    exception = AdminAPIException(
        error=APIError(
            message=_('admin_title'),
            code='test',
            field_errors={
                'test': FieldError(_('throw_error'))
            },
        ),
        status_code=400,
        error_code='test',
    )
    language_manager = CustomLanguageManager('ru')

    translation = {
        'error': {
            'code': 'test',
            'field_errors': {
                'test': {
                    'code': None,
                    'message': 'Пример ошибки валидации поля.',
                },
            },
            'message': 'Brilliance Admin Демо',
        },
        'error_code': 'test',
        'status_code': 400,
    }
    assert exception.model_dump(mode='json', context={'language_manager': language_manager}) == translation


@pytest.mark.asyncio
async def test_translate_context(mocker):
    CustomLanguageManager('ru')
    assert str(_('throw_error')) == 'Пример ошибки валидации поля.'


@pytest.mark.asyncio
async def test_merge(mocker):
    phrases = {
        'ru': {
            'delete': 'Удалить1_ru',
            'new': 'new1_ru',
        },
        'en': {
            'new': 'new_en',
        },
        'pu': {
            'privet': 'privet_pu',
        }
    }
    default_phrases = {
        'ru': {
            'delete': 'Удалить_ru',
            'other': 'other_ru',
        },
        'en': {
            'other': 'other_en'
        },
        'pu': {
            'privet': 'privet_pu_pu_pu',
        }
    }
    new_phrases = merge_phrases(phrases, default_phrases)

    expected = {
        'en': {
            'new': 'new_en',
            'other': 'other_en',
        },
        'pu': {
            'privet': 'privet_pu_pu_pu',
        },
        'ru': {
            'delete': 'Удалить_ru',
            'new': 'new1_ru',
            'other': 'other_ru',
        },
    }
    assert new_phrases == expected
