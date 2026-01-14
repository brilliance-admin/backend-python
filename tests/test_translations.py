import pytest

from brilliance_admin.exceptions import AdminAPIException, APIError, FieldError
from brilliance_admin.translations import TranslateText as _


@pytest.mark.asyncio
async def test_translate_exception(mocker, language_context):
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

    translation = {
        'error': {
            'code': 'test',
            'field_errors': {
                'test': {
                    'code': None,
                    'field_slug': None,
                    'message': 'Пример ошибки валидации поля.',
                },
            },
            'message': 'Brilliance Admin Демо',
        },
        'error_code': 'test',
        'status_code': 400,
    }
    assert exception.model_dump(mode='json', context={'language_context': language_context}) == translation


@pytest.mark.asyncio
async def test_translate_context(mocker, language_context):
    assert str(_('throw_error')) == 'Пример ошибки валидации поля.'
