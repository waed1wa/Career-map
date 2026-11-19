# Карьерная карта

Сервис для студентов: по резюме или короткому опросу строит карту из 6–8 шагов до первой работы
и подбирает учебные проекты. Курс «Технологии разработки ПО», команда: Моисеенко, Якубов, Федотов.

Это **каркас спринта 0**: всё запускается, но бизнес-функций пока почти нет.

## Как устроено (C4, уровень 2)

| Контейнер | Что это | Где в репозитории |
|---|---|---|
| Веб-клиент | React + TypeScript, раздаётся через nginx | `frontend/` |
| API | FastAPI, модульный монолит | `backend/app/` |
| Фоновый обработчик | Celery worker (тот же код, что API) | `backend/app/worker.py` |
| Планировщик | Celery beat, раз в час проверяет сроки заявок | `backend/app/worker.py` |
| База | PostgreSQL 16 + pgvector | `docker-compose.yml` |
| Очередь | Redis | `docker-compose.yml` |
| Файлы | MinIO (резюме) | `docker-compose.yml` |

Модули API совпадают с компонентами уровня 3: `auth`, `profile`, `survey`, `career_map`, `projects`, `catalog`.
Плюс `integrations/llm` — LLM-шлюз.

Модуль `career_map` сделан по гексагональной схеме (уровень 4):
- `domain.py` — ядро: `CareerMap`, `MapStep`, объект-значение `SkillId`;
- `ports.py` — интерфейсы `CatalogRepository`, `Explainer`;
- `builder.py` — построитель карты, без LLM и без случайности;
- `demo_catalog.py` — временный адаптер справочника в памяти.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

- клиент: http://localhost:8080
- API и документация: http://localhost:8000/api/docs
- проверка: http://localhost:8000/api/health → `"status": "ok"`
- MinIO: http://localhost:9001

### Без Docker (для разработки)

```bash
# бэкенд
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
uvicorn app.main:app --reload

# клиент (в другом терминале)
cd frontend
npm install
npm run dev        # http://localhost:5173, /api проксируется на :8000
```

## Что уже есть

- `GET /api/health` — живы ли база и Redis (smoke-тест);
- `GET /api/career-map/demo` — демо-карта для гостя;
- `GET /api/catalog/professions` — список профессий (пока одна);
- остальные модули отвечают `501` с указанием спринта;
- доменная логика заявок: отказ только с причиной, напоминание на 5-й день, «просрочена» на 7-й;
- LLM-шлюз: обезличивание, запасной провайдер, заглушки GigaChat/YandexGPT;
- первая миграция: pgvector + таблица `users`;
- CI на GitHub Actions, pre-commit, правила работы в `docs/CONTRIBUTING.md`.

## Тесты

| Файл | Что проверяет | Тест-кейс из плана |
|---|---|---|
| `test_map_builder.py` | порядок шагов, детерминированность, карта без LLM | TC-01, TC-02, TC-03 |
| `test_llm_gateway.py` | обезличивание, запасной провайдер | TC-04 |
| `test_applications.py` | отказ с причиной, граничные значения 4 д 23 ч / 5 д / 7 д | TC-06, TC-07 |
| `test_health.py` | smoke: приложение поднимается | — |
| `frontend/src/lib/plural.test.ts` | «1 шаг / 3 шага / 5 шагов», классы эквивалентности | — |

## Чек-лист узловой точки УТ1 «Каркас» (15.11)

- [ ] у всех троих `docker compose up` поднимает 7 контейнеров
- [ ] `/api/health` отвечает `ok`
- [ ] CI зелёный на `main`
- [ ] ветка `main` защищена, слияние только через пулл-реквест
- [ ] доска задач заведена, бэклог спринта 1 оценён
- [ ] у каждого хотя бы один слитый пулл-реквест

## Что дальше

| Спринт | Что делаем |
|---|---|
| 1 | вход и роли, лендинг с демо-картой, роутинг в клиенте |
| 2 | загрузка резюме в MinIO, опрос, разбор навыков в фоне |
| 3 | справочник на 60 навыков в базе, карта на React Flow, подключение GigaChat |
| 4 | проекты и заявки, напоминания по срокам, MVP |
