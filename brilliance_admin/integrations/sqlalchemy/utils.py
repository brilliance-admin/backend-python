
COMPOSITE_PK_NOT_SUPPORTED = 'Composite primary key is not supported'


def extract_integrity_detail(exc) -> str:
    orig = getattr(exc, 'orig', None)
    if orig is not None:
        orig_cause = getattr(orig, '__cause__', None)
        if orig_cause is not None:
            table = getattr(orig_cause, 'table_name', None)
            column = getattr(orig_cause, 'column_name', None)
            if table and column:
                return f'{table}.{column}'
            if table:
                return table
            msg = getattr(orig_cause, 'message', '')
            if msg:
                return msg
            if orig_cause.args:
                return str(orig_cause.args[0])
        return str(orig).split('\n')[0]
    return str(exc)


def get_pk(obj):
    pk_cols = obj.__mapper__.primary_key
    if len(pk_cols) != 1:
        raise NotImplementedError(COMPOSITE_PK_NOT_SUPPORTED)
    return getattr(obj, pk_cols[0].key)


def get_pk_field_name(model_or_obj):
    pk_cols = model_or_obj.__mapper__.primary_key
    if len(pk_cols) != 1:
        raise NotImplementedError(COMPOSITE_PK_NOT_SUPPORTED)
    return pk_cols[0].key
