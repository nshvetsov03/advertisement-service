from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app.models import Advertisement
from app.schemas import (
    AdvertisementCreate,
    AdvertisementUpdate,
    AdvertisementResponse,
)

# Создаём таблицы при старте приложения
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Advertisement Service",
    description="REST API сервиса объявлений купли/продажи",
    version="1.0.0",
)


# ---------- POST /advertisement ----------
@app.post(
    "/advertisement",
    response_model=AdvertisementResponse,
    status_code=201,
    summary="Создать объявление",
)
def create_advertisement(
    payload: AdvertisementCreate,
    db: Session = Depends(get_db),
):
    ad = Advertisement(**payload.model_dump())
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


# ---------- GET /advertisement/{advertisement_id} ----------
@app.get(
    "/advertisement/{advertisement_id}",
    response_model=AdvertisementResponse,
    summary="Получить объявление по ID",
)
def get_advertisement(advertisement_id: int, db: Session = Depends(get_db)):
    ad = db.query(Advertisement).filter(Advertisement.id == advertisement_id).first()
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    return ad


# ---------- PATCH /advertisement/{advertisement_id} ----------
@app.patch(
    "/advertisement/{advertisement_id}",
    response_model=AdvertisementResponse,
    summary="Обновить объявление (частично)",
)
def update_advertisement(
    advertisement_id: int,
    payload: AdvertisementUpdate,
    db: Session = Depends(get_db),
):
    ad = db.query(Advertisement).filter(Advertisement.id == advertisement_id).first()
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, value in update_data.items():
        setattr(ad, field, value)

    db.commit()
    db.refresh(ad)
    return ad


# ---------- DELETE /advertisement/{advertisement_id} ----------
@app.delete(
    "/advertisement/{advertisement_id}",
    response_model=AdvertisementResponse,
    summary="Удалить объявление",
)
def delete_advertisement(advertisement_id: int, db: Session = Depends(get_db)):
    ad = db.query(Advertisement).filter(Advertisement.id == advertisement_id).first()
    if ad is None:
        raise HTTPException(status_code=404, detail="Advertisement not found")

    db.delete(ad)
    db.commit()
    return ad


# ---------- GET /advertisement?{query_string} ----------
@app.get(
    "/advertisement",
    response_model=list[AdvertisementResponse],
    summary="Поиск объявлений по полям",
)
def search_advertisements(
    title: Optional[str] = Query(None, description="Поиск по заголовку (contains)"),
    description: Optional[str] = Query(None, description="Поиск по описанию (contains)"),
    price: Optional[float] = Query(None, description="Точное совпадение цены"),
    price_min: Optional[float] = Query(None, description="Минимальная цена (>=)"),
    price_max: Optional[float] = Query(None, description="Максимальная цена (<=)"),
    author: Optional[str] = Query(None, description="Поиск по автору (contains)"),
    date_from: Optional[datetime] = Query(None, description="Дата создания от (>=, формат ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Дата создания до (<=, формат ISO 8601)"),
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