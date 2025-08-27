# 🚀 Быстрый старт с API tnved.info

## Шаг 1: Получение учетных данных

1. Зарегистрируйтесь на [tnved.info](https://tnved.info)
2. Получите логин и пароль для API
3. Убедитесь, что у вас есть действующая лицензия

## Шаг 2: Настройка проекта

### Добавьте переменные в .env файл:
```env
TNVED_INFO_USERNAME=your_username_here
TNVED_INFO_PASSWORD=your_password_here
```

### Запустите сервер:
```bash
uvicorn app.main:app --reload
```

## Шаг 3: Тестирование

### Запустите тестовый скрипт:
```bash
python test_tnved_info_integration.py
```

### Или используйте примеры:
```bash
python examples/tnved_info_usage.py
```

## Шаг 4: Использование API

### Поиск ТН ВЭД кодов:
```bash
curl -X POST "http://localhost:8000/api/v1/tnved-info/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "LED light bulbs"}'
```

### Классификация товара:
```bash
curl -X POST "http://localhost:8000/api/v1/tnved-info/classify" \
  -H "Content-Type: application/json" \
  -d '{"description": "LED light bulbs, 10W, E27 base", "category": "electronics"}'
```

### Получение информации о коде:
```bash
curl "http://localhost:8000/api/v1/tnved-info/code/8539310000"
```

## Шаг 5: Интеграция в код

```python
from app.services.rls_tnved_info import TNVEDInfoService

# Создание сервиса
service = TNVEDInfoService(
    username="your_username",
    password="your_password"
)

# Поиск кодов
result = await service.search_tnved_codes("LED light bulbs")
if result["success"]:
    for item in result["results"]:
        print(f"Код: {item['Code']}, Описание: {item['Description']}")

# Классификация
tnved_info = await service.classify_product(
    description="LED light bulbs, 10W, E27 base",
    category="electronics"
)
```

## 🎯 Готово!

Теперь у вас есть полная интеграция с API tnved.info для:
- ✅ Поиска ТН ВЭД кодов
- ✅ Классификации товаров
- ✅ Получения информации о кодах
- ✅ Мониторинга лицензии

## 📚 Дополнительная документация

- [Полная документация API](tnved-info-api-integration.md)
- [Примеры использования](examples/tnved_info_usage.py)
- [Тестовый скрипт](test_tnved_info_integration.py)
