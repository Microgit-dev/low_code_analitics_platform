from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.services.password_hasher import PasswordHasher
from app.application.services.token_service import TokenService
from app.application.use_cases.auth.login_user import InvalidCredentialsError, LoginUserUseCase
from app.application.use_cases.auth.register_user import RegisterUserUseCase, UserAlreadyExistsError
from app.domain.entities.user import User
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.interfaces.api.dependencies.auth import get_current_user
from app.interfaces.api.dependencies.db import get_db
from app.interfaces.api.v1.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user_repo = SQLAlchemyUserRepository(db)
    register_use_case = RegisterUserUseCase(user_repo, PasswordHasher())

    try:
        created_user = register_use_case.execute(payload.email.lower(), payload.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    token_service = TokenService()
    token = token_service.create_access_token(created_user.id)
    return AuthResponse(access_token=token)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user_repo = SQLAlchemyUserRepository(db)
    login_use_case = LoginUserUseCase(user_repo, PasswordHasher(), TokenService())

    try:
        token = login_use_case.execute(payload.email.lower(), payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    return AuthResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email)
