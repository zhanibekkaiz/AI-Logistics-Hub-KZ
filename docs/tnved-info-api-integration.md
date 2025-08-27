# Интеграция с API tnved.info

## Обзор

Данная интеграция позволяет использовать API сервиса [tnved.info](https://tnved.info) для поиска и классификации кодов ТН ВЭД в рамках проекта AI Logistics Hub.

## Настройка

### 1. Получение учетных данных

1. Зарегистрируйтесь на сайте [tnved.info](https://tnved.info)
2. В профиле пользователя узнайте номер рабочего места
3. Свяжитесь с отделом продаж ТОО "Sector Tree" для приобретения лицензии
4. Получите логин и пароль для доступа к API

### 2. Настройка переменных окружения

Добавьте в файл `.env` следующие переменные:

```env
# TNVED Info API настройки (api.tnved.info)
TNVED_INFO_USERNAME=your_username_here
TNVED_INFO_PASSWORD=your_password_here
```

### 3. Проверка интеграции

Запустите тестовый скрипт для проверки работоспособности:

```bash
python test_tnved_info_integration.py
```

## API Endpoints

### 1. Поиск ТН ВЭД кодов

**POST** `/api/v1/tnved-info/search`

Поиск кодов ТН ВЭД по описанию товара или коду.

**Параметры запроса:**
```json
{
  "query": "LED light bulbs",
  "group": "8539"
}
```

**Ответ:**
```json
{
  "success": true,
  "results": [
    {
      "probability": 96.28,
      "code": "8539310000",
      "description": "ЛАМПЫ СВЕТОДИОДНЫЕ",
      "start_date": "2017-01-01T00:00:00Z",
      "end_date": null,
      "is_old": false
    }
  ],
  "license_info": {
    "work_place": "91036",
    "end_date": "2024-12-31T00:00:00Z",
    "remain": 2947,
    "total": 3000
  },
  "response_state": 200,
  "error_message": null
}
```

**GET** `/api/v1/tnved-info/search?query=LED%20light%20bulbs&group=8539`

Альтернативный способ поиска через GET запрос.

### 2. Получение информации о коде ТН ВЭД

**GET** `/api/v1/tnved-info/code/{tnved_code}`

Получение подробной информации о конкретном коде ТН ВЭД.

**Пример:** `/api/v1/tnved-info/code/8539310000`

**Ответ:**
```json
{
  "code": "8539310000",
  "description": "ЛАМПЫ СВЕТОДИОДНЫЕ",
  "duty_rate": 5.0,
  "vat_rate": 12.0,
  "required_documents": [
    "Инвойс",
    "Упаковочный лист",
    "Сертификат происхождения",
    "Сертификат соответствия",
    "Декларация соответствия"
  ],
  "restrictions": []
}
```

### 3. Классификация товара

**POST** `/api/v1/tnved-info/classify`

Автоматическое определение ТН ВЭД кода по описанию товара.

**Параметры запроса:**
```json
{
  "description": "LED light bulbs, 10W, E27 base, white color, energy efficient",
  "category": "electronics"
}
```

**Ответ:** Аналогичен ответу на получение информации о коде ТН ВЭД.

### 4. Информация о лицензии

**GET** `/api/v1/tnved-info/license`

Получение информации о текущей лицензии API.

**Ответ:**
```json
{
  "work_place": "91036",
  "end_date": "2024-12-31T00:00:00Z",
  "remain": 2947,
  "total": 3000
}
```

### 5. Проверка здоровья API

**GET** `/api/v1/tnved-info/health`

Проверка работоспособности API.

**Ответ:**
```json
{
  "success": true,
  "message": "TNVED API is healthy",
  "data": {
    "status": "healthy"
  }
}
```

### 6. Очистка кэша

**POST** `/api/v1/tnved-info/cache/clear`

Очистка внутреннего кэша сервиса.

**Ответ:**
```json
{
  "success": true,
  "message": "TNVED cache cleared successfully"
}
```

## Коды состояния ответа

API tnved.info возвращает следующие коды состояния:

- **200, 201** - Успешный запрос
- **203** - По запросу ничего не найдено
- **301** - Введён неполный код ТН ВЭД
- **401** - Неавторизованный пользователь
- **403** - Лицензия истекла
- **449** - Обновление информации для поиска (попробуйте снова через несколько секунд)
- **500** - Внутренняя ошибка сервера

## Использование в коде

### Пример использования сервиса

```python
from app.services.rls_tnved_info import TNVEDInfoService

# Создание сервиса
service = TNVEDInfoService(
    username="your_username",
    password="your_password"
)

# Поиск кодов ТН ВЭД
result = await service.search_tnved_codes("LED light bulbs")
if result["success"]:
    for item in result["results"]:
        print(f"Код: {item['Code']}, Описание: {item['Description']}")

# Классификация товара
tnved_info = await service.classify_product(
    description="LED light bulbs, 10W, E27 base",
    category="electronics"
)
if tnved_info:
    print(f"Определён код: {tnved_info.code}")
```

### Интеграция с существующим сервисом TNVED

Новый сервис `TNVEDInfoService` работает параллельно с существующим `TNVEDService` и может быть использован как дополнение или замена в зависимости от потребностей.

## Ограничения и особенности

1. **Лицензирование**: Требуется действующая лицензия от ТОО "Sector Tree"
2. **Лимиты**: API имеет ограничения на количество запросов
3. **Кэширование**: Сервис использует внутренний кэш для оптимизации
4. **Асинхронность**: Все методы асинхронные для лучшей производительности
5. **Обработка ошибок**: Подробное логирование всех ошибок и исключений

## Мониторинг и логирование

Сервис ведёт подробные логи всех операций:

- Поисковые запросы
- Результаты классификации
- Ошибки API
- Информация о лицензии
- Статистика использования

Логи доступны через стандартную систему логирования проекта.

## Поддержка

При возникновении проблем:

1. Проверьте правильность учетных данных
2. Убедитесь в действенности лицензии
3. Проверьте логи приложения
4. Запустите тестовый скрипт для диагностики
5. Обратитесь к документации API tnved.info

## Примеры использования

### Поиск по описанию товара
```bash
curl -X POST "http://localhost:8000/api/v1/tnved-info/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "МАЙКИ ТРИКОТАЖНЫЕ"}'
```

### Получение информации о коде
```bash
curl "http://localhost:8000/api/v1/tnved-info/code/3921906000"
```

### Классификация товара
```bash
curl -X POST "http://localhost:8000/api/v1/tnved-info/classify" \
  -H "Content-Type: application/json" \
  -d '{"description": "LED light bulbs, 10W, E27 base", "category": "electronics"}'
```
