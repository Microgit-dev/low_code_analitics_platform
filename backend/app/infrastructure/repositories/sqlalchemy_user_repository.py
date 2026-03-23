from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.db.models.user_model import UserModel


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user: User) -> User:
        model = UserModel(email=user.email, password_hash=user.password_hash)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return User(id=model.id, email=model.email, password_hash=model.password_hash, created_at=model.created_at)

    def get_by_email(self, email: str) -> User | None:
        model = self.db.query(UserModel).filter(UserModel.email == email).first()
        if not model:
            return None
        return User(id=model.id, email=model.email, password_hash=model.password_hash, created_at=model.created_at)

    def get_by_id(self, user_id: int) -> User | None:
        model = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not model:
            return None
        return User(id=model.id, email=model.email, password_hash=model.password_hash, created_at=model.created_at)
