import sys
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, TomlConfigSettingsSource

IS_TEST = 'pytest' in sys.modules


class Settings(BaseSettings):
    db: str = Field(alias='POSTGRES_DB')
    user: str = Field(alias='POSTGRES_USER')
    password: str = Field(alias='POSTGRES_PASSWORD')

    host: str = Field(alias='POSTGRES_HOST')
    port: str = Field(alias='POSTGRES_PORT', default='5432')
    echo: bool = Field(alias='POSTGRES_ECHO', default=False)
    create_all: bool = Field(alias='POSTGRES_CREATE_ALL', default=False)
    fake_delay_seconds: float = 0 if IS_TEST else 0.2

    model_config = SettingsConfigDict(
        case_sensitive=False,
        populate_by_name=True,
    )

    def get_connection_string(self) -> str:
        if IS_TEST:
            return 'sqlite+aiosqlite:///:memory:'

        return f'postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}'

    # pylint: disable=too-many-positional-arguments
    # pylint: disable=too-many-arguments
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return env_settings, TomlConfigSettingsSource(settings_cls)


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
