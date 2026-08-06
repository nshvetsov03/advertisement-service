# Advertisement Service

REST API сервиса объявлений купли/продажи на FastAPI.

## Эндпоинты

| Метод  | Путь                                      | Описание                         |
|--------|-------------------------------------------|----------------------------------|
| POST   | `/advertisement`                          | Создать объявление               |
| GET    | `/advertisement/{advertisement_id}`       | Получить объявление по ID        |
| PATCH  | `/advertisement/{advertisement_id}`       | Частично обновить объявление     |
| DELETE | `/advertisement/{advertisement_id}`       | Удалить объявление               |
| GET    | `/advertisement?title=&author=&price_min=`| Поиск по полям                   |

## Запуск через Diocker

```bash
docker compose up --build
```

Сервис будет доступен на http://localhost:8000

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Запуск локально (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Примеры запросов

### Создать объявление
```bash
curl -X POST http://localhost:8000/advertisement \
  -H "Content-Type: application/json" \
  -d '{
        "title": "iPhone 13",
        "description": "Продам iPhone 13 128GB, состояние отличное",
        "price": 55000,
        "author": "Иван"
      }'
```

### Получить по ID
```bash
curl http://localhost:8000/advertisement/1
```

### Обновить (частично)
```bash
curl -X PATCH http://localhost:8000/advertisement/1 \
  -H "Content-Type: application/json" \
  -d '{"price": 50000}'
```

### Поиск
```bash
curl "http://localhost:8000/advertisement?title=iPhone&price_min=40000&price_max=60000"
```

### Удалить
```bash
curl -X DELETE http://localhost:8000/advertisement/1
```