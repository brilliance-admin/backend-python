import pytest

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException
from brilliance_admin.schema.table.admin_action import ActionData
from example.main import admin_schema
from example.sections.django_models import (
    DjangoAnotherExample,
    DjangoAnotherExampleFactory,
    DjangoExample,
    DjangoExampleFactory,
)
from tests.django.test_django_subcategory import DjangoExampleAdmin, get_example_another_subcategory


class RestrictedExampleAdmin(DjangoExampleAdmin):
    def get_queryset(self, *, action, action_slug=None):
        return super().get_queryset(action=action, action_slug=action_slug).exclude(title='hidden')


@pytest.mark.asyncio
async def test_update_visible(language_context):
    category = RestrictedExampleAdmin()
    record = await DjangoExampleFactory(title='visible')
    kwargs = {
        'pk': record.pk,
        'data': {'title': 'updated'},
        'user': UserABC(username='test'),
        'language_context': language_context,
        'admin_schema': admin_schema,
        'history_change_provider': None,
    }
    result = await category.update(**kwargs)
    assert result.pk == record.pk
    await record.arefresh_from_db()
    assert record.title == 'updated'


@pytest.mark.asyncio
async def test_update_hidden(language_context):
    category = RestrictedExampleAdmin()
    record = await DjangoExampleFactory(title='hidden')
    kwargs = {
        'pk': record.pk,
        'data': {'title': 'updated'},
        'user': UserABC(username='test'),
        'language_context': language_context,
        'admin_schema': admin_schema,
        'history_change_provider': None,
    }
    with pytest.raises(AdminAPIException) as exc_info:
        await category.update(**kwargs)
    assert exc_info.value.get_error().code == 'record_not_found'
    await record.arefresh_from_db()
    assert record.title == 'hidden'


@pytest.mark.asyncio
async def test_delete_visible():
    category = RestrictedExampleAdmin()
    visible = await DjangoExampleFactory(title='visible')
    hidden = await DjangoExampleFactory(title='hidden')
    pks = [visible.pk]
    await category.delete(action_data=ActionData(pks=pks))
    assert not await DjangoExample.objects.filter(pk=visible.pk).aexists()
    assert await DjangoExample.objects.filter(pk=hidden.pk).aexists()


@pytest.mark.asyncio
async def test_delete_hidden():
    category = RestrictedExampleAdmin()
    visible = await DjangoExampleFactory(title='visible')
    hidden = await DjangoExampleFactory(title='hidden')
    pks = [hidden.pk]
    with pytest.raises(AdminAPIException) as exc_info:
        await category.delete(action_data=ActionData(pks=pks))
    assert exc_info.value.status_code == 404
    assert await DjangoExample.objects.filter(pk=visible.pk).aexists()
    assert await DjangoExample.objects.filter(pk=hidden.pk).aexists()


@pytest.mark.asyncio
async def test_delete_mixed_access():
    category = RestrictedExampleAdmin()
    visible = await DjangoExampleFactory(title='visible')
    hidden = await DjangoExampleFactory(title='hidden')
    pks = [visible.pk, hidden.pk]
    with pytest.raises(AdminAPIException) as exc_info:
        await category.delete(action_data=ActionData(pks=pks))
    assert exc_info.value.status_code == 404
    assert await DjangoExample.objects.filter(pk=visible.pk).aexists()
    assert await DjangoExample.objects.filter(pk=hidden.pk).aexists()


@pytest.mark.asyncio
async def test_delete_missing():
    category = RestrictedExampleAdmin()
    visible = await DjangoExampleFactory(title='visible')
    hidden = await DjangoExampleFactory(title='hidden')
    pks = [visible.pk, max(visible.pk, hidden.pk) + 1]
    with pytest.raises(AdminAPIException) as exc_info:
        await category.delete(action_data=ActionData(pks=pks))
    assert exc_info.value.status_code == 404
    assert await DjangoExample.objects.filter(pk=visible.pk).aexists()
    assert await DjangoExample.objects.filter(pk=hidden.pk).aexists()


@pytest.mark.asyncio
async def test_delete_own_parent(language_context):
    parent_category, category = get_example_another_subcategory()
    parent = await DjangoExampleFactory()
    other_parent = await DjangoExampleFactory()
    own = await DjangoAnotherExampleFactory(example=parent)
    other = await DjangoAnotherExampleFactory(example=other_parent)
    pks = [own.pk]
    kwargs = {
        'request': None,
        'action': 'delete',
        'action_data': ActionData(pks=pks),
        'language_context': language_context,
        'user': UserABC(username='test'),
        'debug': True,
        'parent_category': parent_category,
        'parent_pk': parent.pk,
    }
    await category._perform_action(**kwargs)
    assert not await DjangoAnotherExample.objects.filter(pk=own.pk).aexists()
    assert await DjangoAnotherExample.objects.filter(pk=other.pk).aexists()


@pytest.mark.asyncio
async def test_delete_other_parent(language_context):
    parent_category, category = get_example_another_subcategory()
    parent = await DjangoExampleFactory()
    other_parent = await DjangoExampleFactory()
    own = await DjangoAnotherExampleFactory(example=parent)
    other = await DjangoAnotherExampleFactory(example=other_parent)
    pks = [other.pk]
    kwargs = {
        'request': None,
        'action': 'delete',
        'action_data': ActionData(pks=pks),
        'language_context': language_context,
        'user': UserABC(username='test'),
        'debug': True,
        'parent_category': parent_category,
        'parent_pk': parent.pk,
    }
    with pytest.raises(AdminAPIException) as exc_info:
        await category._perform_action(**kwargs)
    assert exc_info.value.status_code == 404
    assert await DjangoAnotherExample.objects.filter(pk=own.pk).aexists()
    assert await DjangoAnotherExample.objects.filter(pk=other.pk).aexists()


@pytest.mark.asyncio
async def test_delete_mixed_parents(language_context):
    parent_category, category = get_example_another_subcategory()
    parent = await DjangoExampleFactory()
    other_parent = await DjangoExampleFactory()
    own = await DjangoAnotherExampleFactory(example=parent)
    other = await DjangoAnotherExampleFactory(example=other_parent)
    pks = [own.pk, other.pk]
    kwargs = {
        'request': None,
        'action': 'delete',
        'action_data': ActionData(pks=pks),
        'language_context': language_context,
        'user': UserABC(username='test'),
        'debug': True,
        'parent_category': parent_category,
        'parent_pk': parent.pk,
    }
    with pytest.raises(AdminAPIException) as exc_info:
        await category._perform_action(**kwargs)
    assert exc_info.value.status_code == 404
    assert await DjangoAnotherExample.objects.filter(pk=own.pk).aexists()
    assert await DjangoAnotherExample.objects.filter(pk=other.pk).aexists()


@pytest.mark.asyncio
async def test_delete_no_parent(language_context):
    parent_category, category = get_example_another_subcategory()
    parent = await DjangoExampleFactory()
    other_parent = await DjangoExampleFactory()
    own = await DjangoAnotherExampleFactory(example=parent)
    other = await DjangoAnotherExampleFactory(example=other_parent)
    pks = [own.pk]
    kwargs = {
        'request': None,
        'action': 'delete',
        'action_data': ActionData(pks=pks),
        'language_context': language_context,
        'user': UserABC(username='test'),
        'debug': True,
        'parent_category': parent_category,
        'parent_pk': None,
    }
    with pytest.raises(AdminAPIException) as exc_info:
        await category._perform_action(**kwargs)
    assert exc_info.value.status_code == 400
    assert await DjangoAnotherExample.objects.filter(pk=own.pk).aexists()
    assert await DjangoAnotherExample.objects.filter(pk=other.pk).aexists()


@pytest.mark.asyncio
async def test_update_parent(language_context):
    parent_category, category = get_example_another_subcategory()
    parent = await DjangoExampleFactory()
    other_parent = await DjangoExampleFactory()
    child = await DjangoAnotherExampleFactory(example=parent, title='before')

    with pytest.raises(AdminAPIException) as exc_info:
        await category.update(
            pk=child.pk,
            data={'example': other_parent.pk, 'title': 'must not change'},
            user=UserABC(username='test'),
            language_context=language_context,
            parent_category=parent_category,
            parent_pk=parent.pk,
            admin_schema=admin_schema,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.get_error().code == 'parent_change_forbidden'
    await child.arefresh_from_db()
    assert child.example_id == parent.pk
    assert child.title == 'before'
