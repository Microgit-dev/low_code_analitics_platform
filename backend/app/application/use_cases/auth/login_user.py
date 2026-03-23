from app.application.services.password_hasher import PasswordHasher
from app.application.services.token_service import TokenService
from app.domain.repositories.user_repository import UserRepository


class InvalidCredentialsError(Exception):
    pass


class LoginUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
    ) -> None:
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    def execute(self, email: str, password: str) -> str:
        user = self.user_repository.get_by_email(email)
        if not user or not self.password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")

        return self.token_service.create_access_token(user.id)
