# transfers

Прием переводов с внутреннего кошелька на внешний: идемпотентный `POST /api/v1/transfer` + подписанный webhook о результате.

Стек: Python ≥ 3.13, FastAPI, SQLAlchemy (async) + asyncpg, PostgreSQL, Alembic, httpx, structlog, uv.

## Запуск

```bash
cp .env.example .env          # заполнить секреты

docker compose up -d          # postgres

uv sync
uv run alembic upgrade head   # миграции
uv run uvicorn src.main:app --reload
```

Проверки:

```bash
curl localhost:8000/health
uv run pytest -q
```

## API

Авторизация: `Authorization: Bearer <API_TOKEN>`, без него — 401.

`POST /api/v1/transfer`

```json
{
  "external_id": "ord-123",
  "currency": "USDT",
  "amount": "10.5",
  "destination": "external-address",
  "comment": "optional"
}
```

Ответ (`201` — создан, `200` — повтор):

```json
{
  "id": "uuid",
  "external_id": "ord-123",
  "currency": "USDT",
  "amount": "10.5",
  "destination": "external-address",
  "status": "completed"
}
```

## Webhook

После исполнения перевода сервис шлет `POST` на `WEBHOOK__URL`:

```json
{
  "id": "uuid",
  "external_id": "ord-123",
  "amount": "10.5",
  "status": "completed",
  "details": {
    "from_address": "internal-wallet-address",
    "to_address": "external-address",
    "tx_hash": "hex | null"
  }
}
```

Подпись тела — `HMAC-SHA256(sha256(api_key), body)` hex, в заголовке из `WEBHOOK__SIGNATURE_HEADER` (дефолт `X-Signature`). Таймаут и ретраи с экспоненциальным бэкоффом — `WEBHOOK__TIMEOUT_SEC`, `WEBHOOK__MAX_RETRIES`.

## Допущения

- Идемпотентность по `external_id`: повтор (даже с другим payload) возвращает первую запись, `200`, конфликт игнорируется. Гонки закрыты unique-ограничением + `IntegrityError`.
- Webhook отправляется сразу после коммита перевода, в рамках обработки запроса. Недоставка хука статус перевода не меняет, только логируется.
- Повторный `POST` с тем же `external_id` webhook заново не отправляет.
- Исполнение перевода — mock: всегда `completed` с generated `tx_hash` (`failed` только при ошибке БД).
- `status=pending` в webhook не уходит, только `completed`/`failed`.
