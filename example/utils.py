import factory
import inspect
from asgiref.sync import sync_to_async


class SQLAlchemyFactoryBase(factory.alchemy.SQLAlchemyModelFactory):
    @classmethod
    async def _create(cls, model_class, **kwargs):
        if not cls._meta.sqlalchemy_session_factory:
            raise AttributeError("sqlalchemy_session_factory not found")

        async_sessionmaker = cls._meta.sqlalchemy_session_factory

        instance = cls.build(**kwargs)

        async with async_sessionmaker() as session:
            session.add(instance)
            await session.flush()
            await session.commit()
            return instance

    @classmethod
    async def create_async(cls, **kwargs):
        return await cls._create(cls._meta.model, **kwargs)

    @classmethod
    async def create_batch_async(cls, size: int, **kwargs):
        return [await cls.create_async(**kwargs) for _ in range(size)]


class DjangoFactoryBase(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    @classmethod
    async def _create(cls, model_class, *args, **kwargs):
        resolved_args = []
        for value in args:
            if inspect.isawaitable(value):
                value = await value
            resolved_args.append(value)

        resolved_kwargs = {}
        for key, value in kwargs.items():
            if inspect.isawaitable(value):
                value = await value
            resolved_kwargs[key] = value

        return await sync_to_async(super()._create, thread_sensitive=True)(
            model_class,
            *resolved_args,
            **resolved_kwargs,
        )
