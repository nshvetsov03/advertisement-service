from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app.models import User, Token, Advertisement
from app.schemas import (
    UserCreate, UserUpdate, UserResponse,
    LoginRequest, TokenResponse,
    AdvertisementCreate, AdvertisementUpdate, AdvertisementResponse,
)
from app.auth import (
    hash_password, verify_password, create_token,
    get_current_user, require_auth, require_admin,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Advertisement Service",
    description="REST API сервиса объявлений с авторизацией",
    version="2.0.0",
)


# ==================== ПОЛЬЗОВАТЕЛИ ====================

@app.post("/user", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    # Проверяем, не занят ли username
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.patch("/user/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    # user может обновить только себя, admin — кого угодно
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.username is not None:
        user.username = payload.username
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    return user


@app.delete("/user/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    # user может удалить только себя, admin — кого угодно
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return user


# ==================== АВТОРИЗАЦИЯ ====================

@app.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_token(user, db)
    return TokenResponse(token=token.token)


# ==================== ОБЪЯВЛЕНИЯ ====================

@app.post("/advertisement", response_model=AdvertisementResponse, status_code=201)
def create_advertisement(
    payload: AdvertisementCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ad = Advertisement(
        **payload.model_dump(),
        owner_id=current_user.id,
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


@app.get("/advertisement/{advertisement_id}", response_model=AdvertisementResponse)
def get_advertisement(advertisement_id: int, db: Session = Depends(get_db)):
    ad = db.query(Advertisement).filter(Advertisement.id == advertisement_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return ad


@app.patch("/advertisement/{advertisement_id}", response_model=AdvertisementResponse)
def update_advertisement(
    advertisement_id: int,
    payload: AdvertisementUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ad = db.query(Advertisement).filter(Advertisement.id == advertisement_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # user может обновить только своё, admin — любое
    if current_user.role != "admin" and ad.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, value in update_data.items():
        setattr(ad, field, value)

    db.commit()
    db.refresh(ad)
    return ad


@app.delete("/advertisement/{advertisement_id}", response_model=AdvertisementResponse)
def delete_advertisement(
    advertisement_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ad = db.query(Advertisement).filter(Advertisement.id == advertisement_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # user может удалить только своё, admin — любое
    if current_user.role != "admin" and ad.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    db.delete(ad)
    db.commit()
    return ad


@app.get("/advertisement", response_model=list[AdvertisementResponse])
def search_advertisements(
    title: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    price: Optional[float] = Query(None),
    price_min: Optional[float] = Query(None),
    price_max: Optional[float] = Query(None),
    author: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Advertisement)

    if title:
        query = query.filter(Advertisement.title.ilike(f"%{title}%"))
    if description:
        query = query.filter(Advertisement.description.ilike(f"%{description}%"))
    if price is not None:
        query = query.filter(Advertisement.price == price)
    if price_min is not None:
        query = query.filter(Advertisement.price >= price_min)
    if price_max is not None:
        query = query.filter(Advertisement.price <= price_max)
    if author:
        query = query.filter(Advertisement.author.ilike(f"%{author}%"))
    if date_from is not None:
        query = query.filter(Advertisement.created_at >= date_from)
    if date_to is not None:
        query = query.filter(Advertisement.created_at <= date_to)

    return query.order_by(Advertisement.created_at.desc()).offset(offset).limit(limit).all()