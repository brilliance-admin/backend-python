import pytest
from django.db import connection, models

from brilliance_admin.auth import UserABC
from brilliance_admin.exceptions import AdminAPIException, FieldError
from brilliance_admin.integrations.django import DjangoAdmin, DjangoFieldsSchema, DjangoInlineField
from example.sections.django_models import (
    DjangoAnotherExample, DjangoAnotherExampleFactory, DjangoExample, DjangoExampleFactory, DjangoUserFactory)


class DjangoAnotherExampleInlineSchema(DjangoFieldsSchema):
    model = DjangoAnotherExample
    fields = ['id', 'title']


class DjangoExampleInlineAdmin(DjangoAdmin):
    model = DjangoExample
    table_schema = DjangoFieldsSchema(
        model=DjangoExample,
        fields=['id', 'owner', 'title', 'another_examples'],
        another_examples=DjangoInlineField(
            many=True,
            table_schema=DjangoAnotherExampleInlineSchema(),
        ),
    )


class InlineBugParent(models.Model):
    title = models.CharField(max_length=255)

    class Meta:
        app_label = 'sections'
        db_table = 'test_inline_bug_parent'


class InlineBugTarget(models.Model):
    title = models.CharField(max_length=255)

    class Meta:
        app_label = 'sections'
        db_table = 'test_inline_bug_target'

    def __str__(self):
        return self.title


class InlineBugRow(models.Model):
    parent = models.ForeignKey(
        InlineBugParent,
        on_delete=models.CASCADE,
        related_name='items',
    )
    target = models.ForeignKey(
        InlineBugTarget,
        on_delete=models.CASCADE,
        related_name='rows',
    )
    name = models.CharField(max_length=255)
    starts_at = models.TimeField(null=True, blank=True)
    targets = models.ManyToManyField(
        InlineBugTarget,
        related_name='many_rows',
        blank=True,
    )

    class Meta:
        app_label = 'sections'
        db_table = 'test_inline_bug_row'


class InlineBugRowSchema(DjangoFieldsSchema):
    model = InlineBugRow
    fields = ['id', 'target', 'name', 'starts_at', 'targets']


class InlineBugParentAdmin(DjangoAdmin):
    model = InlineBugParent
    table_schema = DjangoFieldsSchema(
        model=InlineBugParent,
        fields=['id', 'title', 'items'],
        items=DjangoInlineField(
            many=True,
            table_schema=InlineBugRowSchema(),
        ),
    )


@pytest.fixture
def inline_bug_schema():
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(InlineBugParent)
        schema_editor.create_model(InlineBugTarget)
        schema_editor.create_model(InlineBugRow)

    yield

    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(InlineBugRow)
        schema_editor.delete_model(InlineBugTarget)
        schema_editor.delete_model(InlineBugParent)


def get_category():
    return DjangoExampleInlineAdmin()


@pytest.mark.asyncio
async def test_inline_retrieve(language_context):
    category = get_category()
    user = UserABC(username='test')

    example = await DjangoExampleFactory()
    child_1 = await DjangoAnotherExampleFactory(example=example, title='child 1')
    child_2 = await DjangoAnotherExampleFactory(example=example, title='child 2')

    result = await category.retrieve(
        pk=example.id,
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert result.data['another_examples'] == [
        {
            'id': child_1.id,
            'title': 'child 1',
        },
        {
            'id': child_2.id,
            'title': 'child 2',
        },
    ]


@pytest.mark.asyncio
async def test_inline_create(language_context):
    category = get_category()
    user = UserABC(username='test')
    owner = await DjangoUserFactory()

    result = await category.create(
        data={
            'owner': owner.id,
            'title': 'parent',
            'another_examples': [
                {'title': 'child 1'},
                {'title': 'child 2'},
            ],
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    created = await DjangoExample.objects.aget(pk=result.pk)
    children = [child async for child in created.another_examples.all().order_by('id')]

    assert [child.title for child in children] == ['child 1', 'child 2']


@pytest.mark.asyncio
async def test_inline_update(language_context):
    category = get_category()
    user = UserABC(username='test')

    example = await DjangoExampleFactory(title='parent')
    child = await DjangoAnotherExampleFactory(example=example, title='child 1')

    update_result = await category.update(
        pk=example.id,
        data={
            'title': 'parent updated',
            'another_examples': [
                {
                    'id': child.id,
                    'title': 'child updated',
                },
                {
                    'title': 'child 2',
                },
            ],
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    assert update_result.pk == example.id

    updated = await DjangoExample.objects.aget(pk=example.id)
    children = [child async for child in updated.another_examples.all().order_by('id')]

    assert [child.title for child in children] == ['child updated', 'child 2']


@pytest.mark.asyncio
async def test_inline_update_accepts_related_field_payload(language_context, inline_bug_schema):
    category = InlineBugParentAdmin()
    user = UserABC(username='test')

    parent = await InlineBugParent.objects.acreate(title='list_342')
    target = await InlineBugTarget.objects.acreate(id=4, title='target')

    await category.update(
        pk=parent.pk,
        data={
            'title': 'list_342',
            'items': [
                {
                    'target': {'key': target.pk, 'title': 'target'},
                    'name': 'item',
                    'starts_at': '12:00',
                },
            ],
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    row = await InlineBugRow.objects.aget(parent=parent)

    assert row.target_id == target.pk
    assert row.name == 'item'
    assert row.starts_at.isoformat(timespec='minutes') == '12:00'

    with pytest.raises(AdminAPIException) as exc:
        await category.update(
            pk=parent.pk,
            data={
                'title': 'list_342',
                'items': [
                    {},
                ],
            },
            user=user,
            language_context=language_context,
            debug=True,
        )

    assert exc.value.status_code == 400
    assert exc.value.error.code == 'validation_error'
    assert exc.value.error.field_errors == {
        'items': FieldError(
            message=[
                {
                    'target': FieldError(
                        message='Field is required',
                        code='field_required',
                    ),
                    'name': FieldError(
                        message='Field is required',
                        code='field_required',
                    ),
                },
            ],
            code='inline_nested',
        ),
    }


@pytest.mark.asyncio
async def test_inline_update_accepts_many_to_many_related_field(language_context, inline_bug_schema):
    category = InlineBugParentAdmin()
    user = UserABC(username='test')

    parent = await InlineBugParent.objects.acreate(title='list_342')
    target = await InlineBugTarget.objects.acreate(id=4, title='target')
    many_target = await InlineBugTarget.objects.acreate(id=5, title='many target')

    await category.update(
        pk=parent.pk,
        data={
            'title': 'list_342',
            'items': [
                {
                    'target': {'key': target.pk, 'title': 'target'},
                    'targets': [{'key': many_target.pk, 'title': 'many target'}],
                    'name': 'item',
                },
            ],
        },
        user=user,
        language_context=language_context,
        debug=True,
    )

    row = await InlineBugRow.objects.aget(parent=parent)
    targets = [item async for item in row.targets.all()]

    assert [item.pk for item in targets] == [many_target.pk]


@pytest.mark.asyncio
async def test_inline_create_rolls_back_parent_if_inline_save_fails(language_context, inline_bug_schema):
    category = InlineBugParentAdmin()
    user = UserABC(username='test')

    with pytest.raises(AdminAPIException):
        await category.create(
            data={
                'title': 'parent',
                'items': [
                    {
                        'target': {'key': 404, 'title': 'missing'},
                        'name': 'item',
                    },
                ],
            },
            user=user,
            language_context=language_context,
            debug=True,
        )

    assert await InlineBugParent.objects.acount() == 0
    assert await InlineBugRow.objects.acount() == 0
