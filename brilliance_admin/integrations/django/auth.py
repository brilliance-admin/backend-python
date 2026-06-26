import inspect

from brilliance_admin.auth import AdminAuthentication, AuthData, AuthResult, UserResult
from brilliance_admin.exceptions import AdminAPIException, APIError
from brilliance_admin.utils import get_logger

logger = get_logger()


class DjangoJWTAdminAuthentication(AdminAuthentication):
    secret: str
    user_model = None
    pk_name = None
    admin_field_name = None
    password_validator = None

    def __init__(self, secret: str, user_model, pk_name='id', admin_field_name='is_admin', password_validator=None):
        self.pk_name = pk_name
        self.secret = secret
        self.user_model = user_model
        self.admin_field_name = admin_field_name
        self.password_validator = password_validator

        if self.password_validator and not callable(self.password_validator):
            raise ValueError("password_validator must be callable")

        if not isinstance(secret, str) or not secret:
            raise ValueError("JWT secret must be a non-empty string")

        if not isinstance(self.admin_field_name, str) or not self.admin_field_name:
            raise ValueError("admin_field_name must be a non-empty string")

        try:
            import jwt
        except ImportError as e:
            raise RuntimeError("PyJWT is not installed. Install it with: pip install pyjwt") from e

        assert hasattr(jwt, "encode"), "PyJWT is not installed"

        fields = {field.name for field in user_model._meta.fields}
        required = {self.pk_name, "username", self.admin_field_name}
        missing = required - fields
        if missing:
            raise ValueError(f"user_model is missing required columns: {', '.join(sorted(missing))}")

    async def login(self, data: AuthData, debug: bool = False) -> AuthResult:
        user = await self.user_model.objects.filter(username=data.username).afirst()
        if not user:
            raise AdminAPIException(APIError(code="user_not_found"), status_code=401)

        try:
            if self.password_validator:
                if inspect.iscoroutinefunction(self.password_validator):
                    valid_password = await self.password_validator(user, data.password)
                else:
                    valid_password = self.password_validator(user, data.password)

                if not valid_password:
                    raise AdminAPIException(APIError(code="user_not_found"), status_code=401)
        except AdminAPIException:
            raise
        except Exception as e:
            logger.exception('Password validator %s exception: %s', self.password_validator, e)
            raise AdminAPIException(
                APIError(message=type(e).__name__ if not debug else str(e), code="password_exception"),
                status_code=500,
            ) from e

        if not getattr(user, self.admin_field_name):
            raise AdminAPIException(APIError(code="not_an_admin"), status_code=401)

        return AuthResult(
            token=self.get_token(user),
            user=UserResult(username=user.username),
        )

    def get_token(self, user):
        import jwt

        return jwt.encode(
            {"user_pk": str(getattr(user, self.pk_name))},
            self.secret,
            algorithm="HS256",
        )

    async def authenticate(self, headers: dict):
        import jwt

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

        user = await self.user_model.objects.filter(
            **{self.pk_name: user_pk, self.admin_field_name: True}
        ).afirst()
        if not user:
            raise AdminAPIException(
                APIError(message="User not found", code="user_not_found"),
                status_code=401,
            )

        return user
