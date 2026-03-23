from app.application.services.password_hasher import PasswordHasher
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository


class UserAlreadyExistsError(Exception):
    pass


class RegisterUserUseCase:
    def __init__(self, user_repository: UserRepository, password_hasher: PasswordHasher) -> None:
        self.user_repository = user_repository
        self.password_hasher = password_hasher

    def execute(self, email: str, password: str) -> User:
        existing_user = self.user_repository.get_by_email(email)
        if existing_user:
            raise UserAlreadyExistsError("User with this email already exists")

        user = User(id=None, email=email, password_hash=self.password_hasher.hash(password))
        return self.user_repository.create(user)
