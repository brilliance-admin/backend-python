from brilliance_admin.auth import AdminAuthentication, AuthData, AuthResult, UserABC, UserResult
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.translations import TranslateText as _
from brilliance_admin.utils import get_logger

logger = get_logger()


class SQLAlchemyJWTAdminAuthentication(AdminAuthentication):
    secret: str
    db_async_session = None
    user_model = None
    pk_name = None

    def __init__(self, secret: str, db_async_session, user_model, pk_name='id'):
        self.pk_name = pk_name
        self.secret = secret
        self.db_async_session = db_async_session
        self.user_model = user_model

        if not isinstance(secret, str) or not secret:
            raise ValueError("JWT secret must be a non-empty string")

        # pylint: disable=import-outside-toplevel
        from sqlalchemy.inspection import inspect
        try:
            import jwt
        except ImportError as e:
            msg = "PyJWT is not installed. Install it with: pip install pyjwt"
            raise RuntimeError(msg) from e

        assert hasattr(jwt, "encode"), "PyJWT is not installed"

        mapper = inspect(user_model)
        columns = {col.key for col in mapper.columns}

        required = {self.pk_name, "username", "is_admin"}
        missing = required - columns

        if missing:
            msg = f"user_model is missing required columns: {', '.join(sorted(missing))}"
            raise ValueError(msg)

    async def login(self, data: AuthData) -> AuthResult:
        # pylint: disable=import-outside-toplevel
        from sqlalchemy import select

        stmt = select(self.user_model).where(self.user_model.username == data.username)
        try:
            async with self.db_async_session() as session:
                result = await session.execute(stmt)

        except ConnectionRefusedError as e:
            logger.exception(
                'SQLAlchemy %s login db error: %s', type(self).__name__, e,
            )
            msg = _('errors.connection_refused_error') % {'error': str(e)}
            raise AdminAPIException(
                APIError(message=msg, code='connection_refused_error'),
                status_code=500,
            ) from e

        user = result.scalar_one_or_none()

        if not user:
            raise AdminAPIException(APIError(code="user_not_found"), status_code=401)

        if not user.is_admin:
            raise AdminAPIException(APIError(code="not_an_admin"), status_code=401)

        return AuthResult(
            token=self.get_token(user),
            user=UserResult(username=user.username),
        )

    def get_token(self, user):
        # pylint: disable=import-outside-toplevel
        import jwt

        return jwt.encode(
            {"user_pk": str(user.id)},
            self.secret,
            algorithm="HS256",
        )

    async def authenticate(self, headers: dict) -> UserABC:
        # pylint: disable=import-outside-toplevel
        import jwt
        from sqlalchemy import inspect, select

        token = headers.get("Authorization")
        if not token:
            raise AdminAPIException(
                APIError(message="Token is not presented"),
                status_code=401,
            )

        token = token.replace("Token ", "")

        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
        except jwt.exceptions.DecodeError as e:
            raise AdminAPIException(
                APIError(message="Token decoding error", code="token_error"),
                status_code=401,
            ) from e

        user_pk = payload.get("user_pk")
        if not user_pk:
            raise AdminAPIException(
                APIError(message="Invalid token payload", code="token_error"),
                status_code=401,
            )

        col = inspect(self.user_model).mapper.columns[self.pk_name]
        python_type = col.type.python_type

        stmt = select(self.user_model).where(
            getattr(self.user_model, self.pk_name) == python_type(user_pk),
            self.user_model.is_admin.is_(True),
        )
        try:
            async with self.db_async_session() as session:
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

        except ConnectionRefusedError as e:
            logger.exception(
                'SQLAlchemy %s authenticate db error: %s', type(self).__name__, e,
            )
            msg = _('errors.connection_refused_error') % {'error': str(e)}
            raise AdminAPIException(
                APIError(message=msg, code='connection_refused_error'),
                status_code=500,
            ) from e

        if not user:
            raise AdminAPIException(
                APIError(message="User not found", code="user_not_found"),
                status_code=401,
            )

        return user
