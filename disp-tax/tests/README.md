# Tests

Тесты для Telegram Dispatcher Platform.

## Запуск тестов

```bash
# Все тесты
pytest

# С покрытием кода
pytest --cov=src --cov-report=html

# Конкретный файл
pytest tests/test_order_fsm.py

# Конкретный тест
pytest tests/test_order_fsm.py::TestOrderFSM::test_can_transition_draft_to_preview
```

## Структура тестов

- `test_order_fsm.py` - Тесты FSM для заказов
- `test_order_service.py` - Тесты сервиса заказов
- `test_anti_ban.py` - Тесты Anti-Ban логики
- `test_response_service.py` - Тесты обработки ответов
- `test_integration.py` - End-to-end тесты

## Фикстуры

- `db_session` - Сессия БД для тестов (in-memory SQLite)
- `sample_dispatcher` - Тестовый диспетчер
- `sample_order` - Тестовый заказ

