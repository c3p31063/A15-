# A15 ガイドライン準拠チェッカー（Django + FastAPI）

## 起動手順
```bash
docker compose build
docker compose run --rm django bash -lc "python manage.py makemigrations core && python manage.py migrate && python manage.py createsuperuser"
docker compose up
```

- Django UI: http://localhost:8000/
- FastAPI health: http://localhost:8001/health

## 構成
- Django: 認証・UI・履歴・承認
- FastAPI: 判定エンジン (/check/text, /check/image)
- PostgreSQL, Redis
```
a15_full/
  docker-compose.yml
  .env
  fastapi/
  django/
```
