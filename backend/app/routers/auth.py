from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import require_role
from app.models import Role, User
from app.schemas import DoctorRead, LoginRequest, Token, UserCreate, UserRead


router = APIRouter()


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email, User.role == payload.role))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email, password, or role")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(str(user.id), user.role.value)
    return Token(access_token=token, role=user.role, full_name=user.full_name)


@router.post("/users", response_model=UserRead)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor))):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        specialty=payload.specialty,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/doctors", response_model=list[DoctorRead])
def list_doctors(db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    return list(db.scalars(select(User).where(User.role == Role.doctor, User.is_active.is_(True)).order_by(User.full_name)))
