from asgiref.sync import sync_to_async
from brilliance_admin.exceptions import FieldError
from brilliance_admin.schema.table.fields.base import RelatedField

MISSING_RECORD_IN_CONTEXT = 'Missing record in serialize context in value: {value}'
RELATED_MISSING_ON_RECORD = (
    'Inline related field "{rel_name}" cannot be serialized from record "{record_type}". '
    'Expected inline row model to contain this relation.'
)
MANY_RELATED_MISSING = 'Many Related field "{rel_name}" is missing on record "{record}"'


class DjangoRelatedField(RelatedField):
    async def serialize(self, value, extra: dict, *args, **kwargs):
        if not value:
            return None

        record = extra.get('record')
        if record is None:
            raise FieldError(MISSING_RECORD_IN_CONTEXT.format(value=value))

        if not hasattr(type(record), self.rel_name):
            raise FieldError(RELATED_MISSING_ON_RECORD.format(
                rel_name=self.rel_name,
                record_type=type(record).__name__,
            ))

        if self.many:
            related = await sync_to_async(lambda: list(getattr(record, self.rel_name).all()), thread_sensitive=True)()
            if related is None:
                raise FieldError(MANY_RELATED_MISSING.format(rel_name=self.rel_name, record=record))
            return [{'key': obj.pk, 'title': str(obj)} for obj in related]

        related = await sync_to_async(getattr, thread_sensitive=True)(record, self.rel_name, None)

        if related is None:
            return None

        return {'key': related.pk, 'title': str(related)}
