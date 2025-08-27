# 🏗 Техническая архитектура AI Logistics Hub

## 🎯 Общая архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   External      │
│   (React/Vue)   │◄──►│   (Python)      │◄──►│   APIs          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   Database      │    │   AI Services   │
│   Instagram Bot │    │   (PostgreSQL)  │    │   (GPT-4o)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠 Технологический стек

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL + Redis (кэш)
- **ORM**: SQLAlchemy
- **Authentication**: JWT tokens
- **API Documentation**: Swagger/OpenAPI

### Frontend
- **Framework**: React.js + TypeScript
- **UI Library**: Material-UI или Ant Design
- **State Management**: Redux Toolkit
- **Build Tool**: Vite
- **Deployment**: Vercel/Netlify

### Боты
- **Telegram**: python-telegram-bot
- **Instagram**: ManyChat API
- **WhatsApp**: WhatsApp Business API

### AI/ML
- **LLM**: OpenAI GPT-4o
- **Document Processing**: Unstructured.io
- **Vector Database**: Pinecone/Weaviate
- **Embeddings**: OpenAI text-embedding-ada-002

### Интеграции
- **Airtable**: тарифы и CRM
- **tnved.info**: коды ТН ВЭД
- **keden.kz**: таможенные данные
- **Qichacha/Tianyancha**: проверка поставщиков
- **ImportYeti**: экспортная история

## 📊 Структура базы данных

### Основные таблицы

```sql
-- Пользователи
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id VARCHAR(50) UNIQUE,
    instagram_id VARCHAR(50),
    email VARCHAR(255),
    phone VARCHAR(20),
    company_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Запросы на расчёт
CREATE TABLE calculation_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    weight DECIMAL(10,2),
    volume DECIMAL(10,2),
    category VARCHAR(100),
    origin VARCHAR(100),
    destination VARCHAR(100),
    tnved_code VARCHAR(20),
    cargo_price DECIMAL(10,2),
    white_price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Поставщики
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    registration_number VARCHAR(100),
    registration_date DATE,
    capital DECIMAL(15,2),
    licenses TEXT[],
    court_cases INTEGER,
    export_history TEXT,
    reliability_score INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Тарифы
CREATE TABLE tariffs (
    id SERIAL PRIMARY KEY,
    route VARCHAR(100),
    service_type VARCHAR(50), -- cargo/white
    weight_from DECIMAL(10,2),
    weight_to DECIMAL(10,2),
    price_per_kg DECIMAL(10,2),
    transit_time INTEGER, -- days
    valid_from DATE,
    valid_to DATE
);
```

## 🔄 API Endpoints

### Основные эндпоинты

```python
# Калькулятор доставки
POST /api/v1/calculate
{
    "weight": 100.5,
    "volume": 0.5,
    "category": "electronics",
    "origin": "Shenzhen",
    "destination": "Almaty"
}

# Проверка поставщика
POST /api/v1/supplier/check
{
    "company_name": "Shenzhen Electronics Co",
    "registration_number": "91440300..."
}

# Определение ТН ВЭД
POST /api/v1/tnved/classify
{
    "description": "LED light bulbs, 10W, E27 base"
}

# Получение тарифов
GET /api/v1/tariffs?route=shenzhen-almaty&type=cargo
```

## 🤖 Архитектура ботов

### Telegram Bot

```python
# Структура состояний
class BotStates:
    AWAITING_WEIGHT = "awaiting_weight"
    AWAITING_VOLUME = "awaiting_volume"
    AWAITING_CATEGORY = "awaiting_category"
    AWAITING_ORIGIN = "awaiting_origin"
    AWAITING_DESTINATION = "awaiting_destination"
    SHOWING_RESULTS = "showing_results"

# Основные команды
/start - Начать расчёт
/calculate - Новый расчёт
/supplier - Проверить поставщика
/help - Помощь
```

### Instagram Bot (ManyChat)

```javascript
// Webhook обработчики
app.post('/webhook/instagram', (req, res) => {
    const { message, user } = req.body;
    
    // Обработка входящих сообщений
    if (message.type === 'text') {
        handleTextMessage(message, user);
    }
    
    res.status(200).send('OK');
});
```

## 🔐 Безопасность

### Аутентификация
- JWT токены для API
- OAuth 2.0 для социальных сетей
- Rate limiting (100 запросов/час на пользователя)

### Защита данных
- HTTPS для всех соединений
- Шифрование чувствительных данных
- GDPR compliance
- Логирование доступа

### API Security
- API ключи для внешних интеграций
- Валидация входных данных
- SQL injection protection
- CORS настройки

## 📈 Масштабирование

### Горизонтальное масштабирование
- Load balancer (Nginx)
- Микросервисная архитектура
- Кэширование (Redis)
- CDN для статических файлов

### Мониторинг
- Prometheus + Grafana
- Sentry для ошибок
- Log aggregation (ELK stack)
- Health checks

## 🚀 Деплоймент

### CI/CD Pipeline
```yaml
# GitHub Actions
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to production
        run: |
          docker build -t ai-logistics-hub .
          docker push registry/ai-logistics-hub
```

### Инфраструктура
- **Production**: AWS/GCP
- **Staging**: Docker Compose
- **Development**: Local environment

## 📋 Чек-лист разработки

### Этап 1: MVP (3-4 недели)
- [ ] Настройка проекта и окружения
- [ ] База данных и основные модели
- [ ] Telegram бот (базовый функционал)
- [ ] Интеграция с Airtable
- [ ] Простой калькулятор

### Этап 2: Расширение (4-6 недель)
- [ ] Веб-интерфейс
- [ ] Instagram бот
- [ ] Интеграция с tnved.info
- [ ] AI для классификации товаров
- [ ] Проверка поставщиков

### Этап 3: Оптимизация (2-3 недели)
- [ ] Кэширование и оптимизация
- [ ] Мониторинг и логирование
- [ ] Тестирование и багфиксы
- [ ] Документация API
