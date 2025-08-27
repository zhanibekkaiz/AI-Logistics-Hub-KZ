# 🔗 Диаграмма интеграций AI Logistics Hub

## 📊 Общая схема системы

```mermaid
graph TB
    %% Входные каналы
    subgraph "ВХОДНЫЕ КАНАЛЫ"
        TG[📱 Telegram Bot]
        IG[📸 Instagram Bot]
        WA[💬 WhatsApp Bot]
        WEB[🌐 Web Form]
    end

    %% API Gateway
    subgraph "API GATEWAY"
        API[FastAPI Gateway]
        VAL[Validation]
        ROUTE[Routing]
    end

    %% Основной движок
    subgraph "CORE PROCESSING ENGINE"
        ORCH[Request Orchestrator]
        ENRICH[Data Enrichment]
        AI[AI Processing]
        REPORT[Report Generator]
        NOTIFY[Notification System]
    end

    %% Внешние интеграции
    subgraph "EXTERNAL INTEGRATIONS"
        TNVED[TNVED.INFO API]
        QICH[Qichacha API]
        AIR[Airtable]
        GPT[OpenAI/GPT]
    end

    %% Хранилище данных
    subgraph "DATA STORAGE"
        AIR_CRM[Airtable CRM]
        CACHE[Redis Cache]
        ANALYTICS[Analytics DB]
    end

    %% Выходные каналы
    subgraph "OUTPUT CHANNELS"
        TG_OUT[📱 Telegram Report]
        EMAIL[📧 Email Report]
        DASH[🌐 Web Dashboard]
        ANALYTICS_OUT[📊 Analytics]
    end

    %% Связи входных каналов
    TG --> API
    IG --> API
    WA --> API
    WEB --> API

    %% API Gateway обработка
    API --> VAL
    VAL --> ROUTE
    ROUTE --> ORCH

    %% Основной процесс
    ORCH --> ENRICH
    ENRICH --> AI
    AI --> REPORT
    REPORT --> NOTIFY

    %% Интеграции с внешними сервисами
    ENRICH --> TNVED
    ENRICH --> QICH
    ENRICH --> AIR
    AI --> GPT

    %% Хранение данных
    REPORT --> AIR_CRM
    ENRICH --> CACHE
    REPORT --> ANALYTICS

    %% Выходные каналы
    NOTIFY --> TG_OUT
    NOTIFY --> EMAIL
    NOTIFY --> DASH
    ANALYTICS --> ANALYTICS_OUT

    %% Стили
    classDef inputChannel fill:#e1f5fe
    classDef gateway fill:#f3e5f5
    classDef engine fill:#e8f5e8
    classDef integration fill:#fff3e0
    classDef storage fill:#fce4ec
    classDef output fill:#e0f2f1

    class TG,IG,WA,WEB inputChannel
    class API,VAL,ROUTE gateway
    class ORCH,ENRICH,AI,REPORT,NOTIFY engine
    class TNVED,QICH,AIR,GPT integration
    class AIR_CRM,CACHE,ANALYTICS storage
    class TG_OUT,EMAIL,DASH,ANALYTICS_OUT output
```

## 🔄 Детальный процесс обработки запроса

```mermaid
sequenceDiagram
    participant Client as Клиент
    participant Gateway as API Gateway
    participant Orchestrator as Request Orchestrator
    participant TNVED as TNVED.INFO API
    participant Qichacha as Qichacha API
    participant Airtable as Airtable
    participant GPT as OpenAI/GPT
    participant Report as Report Generator
    participant CRM as Airtable CRM
    participant Output as Output Channels

    Client->>Gateway: Отправка запроса
    Note over Client: Описание товара, вес,<br/>объем, поставщик, маршрут

    Gateway->>Gateway: Валидация данных
    Gateway->>Orchestrator: Передача запроса

    Orchestrator->>TNVED: Запрос кода ТН ВЭД
    TNVED-->>Orchestrator: Код, пошлины, документы

    Orchestrator->>Qichacha: Проверка поставщика
    Qichacha-->>Orchestrator: Данные о компании, риски

    Orchestrator->>Airtable: Получение тарифов
    Airtable-->>Orchestrator: Тарифы карго/белая доставка

    Orchestrator->>GPT: Передача всех данных для анализа
    Note over GPT: Интерпретация TNVED,<br/>анализ поставщика,<br/>расчет логистики

    GPT-->>Orchestrator: Структурированный анализ

    Orchestrator->>Report: Генерация отчета
    Report-->>Orchestrator: Готовый отчет

    Orchestrator->>CRM: Сохранение в базу
    Orchestrator->>Output: Отправка клиенту

    Output-->>Client: Структурированный отчет
    Note over Client: Рекомендации по доставке,<br/>анализ поставщика,<br/>требования по документам
```

## 🧠 AI Processing Flow

```mermaid
graph LR
    subgraph "INPUT DATA"
        TNVED_DATA[TNVED Data<br/>• Code<br/>• Duty rates<br/>• Documents]
        SUPPLIER_DATA[Supplier Data<br/>• Company info<br/>• Risk assessment<br/>• History]
        LOGISTICS_DATA[Logistics Data<br/>• Cargo rates<br/>• White rates<br/>• Routes]
    end

    subgraph "AI PROCESSING"
        TNVED_AI[TNVED Interpreter<br/>• Duty calculation<br/>• Compliance analysis<br/>• Document requirements]
        SUPPLIER_AI[Supplier Analyzer<br/>• Risk assessment<br/>• Reliability score<br/>• Recommendations]
        LOGISTICS_AI[Logistics Calculator<br/>• Cost optimization<br/>• Route selection<br/>• Timeline planning]
    end

    subgraph "AI SYNTHESIS"
        ANALYSIS[Comprehensive Analysis<br/>• Best delivery option<br/>• Risk factors<br/>• Cost-benefit analysis]
        RECOMMENDATIONS[AI Recommendations<br/>• Delivery type<br/>• Required actions<br/>• Risk mitigation]
    end

    subgraph "OUTPUT"
        REPORT[Structured Report<br/>• Executive summary<br/>• Detailed analysis<br/>• Action items]
    end

    TNVED_DATA --> TNVED_AI
    SUPPLIER_DATA --> SUPPLIER_AI
    LOGISTICS_DATA --> LOGISTICS_AI

    TNVED_AI --> ANALYSIS
    SUPPLIER_AI --> ANALYSIS
    LOGISTICS_AI --> ANALYSIS

    ANALYSIS --> RECOMMENDATIONS
    RECOMMENDATIONS --> REPORT

    classDef input fill:#e3f2fd
    classDef processing fill:#f3e5f5
    classDef synthesis fill:#e8f5e8
    classDef output fill:#fff3e0

    class TNVED_DATA,SUPPLIER_DATA,LOGISTICS_DATA input
    class TNVED_AI,SUPPLIER_AI,LOGISTICS_AI processing
    class ANALYSIS,RECOMMENDATIONS synthesis
    class REPORT output
```

## 📊 Data Flow Architecture

```mermaid
graph TD
    subgraph "CLIENT INPUT"
        INPUT[Client Request<br/>• Product description<br/>• Weight/Volume<br/>• Origin/Destination<br/>• Supplier name]
    end

    subgraph "DATA ENRICHMENT"
        TNVED_ENRICH[TNVED Enrichment<br/>• Code identification<br/>• Duty calculation<br/>• Document requirements]
        SUPPLIER_ENRICH[Supplier Enrichment<br/>• Company verification<br/>• Risk assessment<br/>• Export history]
        LOGISTICS_ENRICH[Logistics Enrichment<br/>• Rate calculation<br/>• Route optimization<br/>• Timeline planning]
    end

    subgraph "AI ANALYSIS"
        GPT_ANALYSIS[GPT Analysis<br/>• Data interpretation<br/>• Risk evaluation<br/>• Recommendation generation]
    end

    subgraph "REPORT GENERATION"
        STRUCTURED[Structured Report<br/>• Executive summary<br/>• Detailed breakdown<br/>• Action recommendations]
    end

    subgraph "OUTPUT & STORAGE"
        CLIENT_OUTPUT[Client Output<br/>• Telegram/Email<br/>• Web dashboard]
        CRM_STORAGE[CRM Storage<br/>• Lead management<br/>• Request tracking]
        ANALYTICS_STORAGE[Analytics<br/>• Performance metrics<br/>• Business intelligence]
    end

    INPUT --> TNVED_ENRICH
    INPUT --> SUPPLIER_ENRICH
    INPUT --> LOGISTICS_ENRICH

    TNVED_ENRICH --> GPT_ANALYSIS
    SUPPLIER_ENRICH --> GPT_ANALYSIS
    LOGISTICS_ENRICH --> GPT_ANALYSIS

    GPT_ANALYSIS --> STRUCTURED

    STRUCTURED --> CLIENT_OUTPUT
    STRUCTURED --> CRM_STORAGE
    STRUCTURED --> ANALYTICS_STORAGE

    classDef input fill:#e1f5fe
    classDef enrichment fill:#f3e5f5
    classDef analysis fill:#e8f5e8
    classDef report fill:#fff3e0
    classDef output fill:#fce4ec

    class INPUT input
    class TNVED_ENRICH,SUPPLIER_ENRICH,LOGISTICS_ENRICH enrichment
    class GPT_ANALYSIS analysis
    class STRUCTURED report
    class CLIENT_OUTPUT,CRM_STORAGE,ANALYTICS_STORAGE output
```

## 🔧 Техническая архитектура интеграций

```mermaid
graph TB
    subgraph "FRONTEND LAYER"
        BOTS[Bot Interfaces<br/>• Telegram<br/>• Instagram<br/>• WhatsApp]
        WEB[Web Interface<br/>• React/Vue.js<br/>• Form handling]
    end

    subgraph "API LAYER"
        GATEWAY[API Gateway<br/>• FastAPI<br/>• Request routing<br/>• Rate limiting]
        AUTH[Authentication<br/>• JWT tokens<br/>• API keys]
    end

    subgraph "BUSINESS LOGIC"
        ORCHESTRATOR[Request Orchestrator<br/>• Process coordination<br/>• Error handling]
        ENRICHMENT[Data Enrichment<br/>• External API calls<br/>• Data validation]
        AI_ENGINE[AI Engine<br/>• GPT integration<br/>• Report generation]
    end

    subgraph "EXTERNAL APIs"
        TNVED_API[TNVED.INFO<br/>• TNVED codes<br/>• Duty rates]
        QICH_API[Qichacha<br/>• Supplier verification<br/>• Risk assessment]
        AIRTABLE_API[Airtable<br/>• Tariffs<br/>• CRM data]
        GPT_API[OpenAI/GPT<br/>• Data interpretation<br/>• Analysis]
    end

    subgraph "DATA LAYER"
        CACHE[Redis Cache<br/>• API responses<br/>• Session data]
        CRM[Airtable CRM<br/>• Leads<br/>• Requests<br/>• Results]
        ANALYTICS[Analytics DB<br/>• Metrics<br/>• Reports]
    end

    BOTS --> GATEWAY
    WEB --> GATEWAY
    GATEWAY --> AUTH
    AUTH --> ORCHESTRATOR
    ORCHESTRATOR --> ENRICHMENT
    ENRICHMENT --> AI_ENGINE

    ENRICHMENT --> TNVED_API
    ENRICHMENT --> QICH_API
    ENRICHMENT --> AIRTABLE_API
    AI_ENGINE --> GPT_API

    ENRICHMENT --> CACHE
    AI_ENGINE --> CRM
    AI_ENGINE --> ANALYTICS

    classDef frontend fill:#e3f2fd
    classDef api fill:#f3e5f5
    classDef business fill:#e8f5e8
    classDef external fill:#fff3e0
    classDef data fill:#fce4ec

    class BOTS,WEB frontend
    class GATEWAY,AUTH api
    class ORCHESTRATOR,ENRICHMENT,AI_ENGINE business
    class TNVED_API,QICH_API,AIRTABLE_API,GPT_API external
    class CACHE,CRM,ANALYTICS data
```

## 📈 Преимущества архитектуры

### **Для клиента:**
- 🎯 **Единый интерфейс** через любой канал
- 📊 **Структурированный отчет** вместо сырых данных
- 🤖 **AI-рекомендации** на основе комплексного анализа
- ⚡ **Быстрый ответ** (2-3 минуты)

### **Для бизнеса:**
- 🔄 **Полная автоматизация** обработки запросов
- 📈 **Масштабируемость** системы
- 📊 **Детальная аналитика** и метрики
- 💼 **CRM интеграция** для управления лидами

### **Технические:**
- 🏗️ **Микросервисная архитектура**
- ⚡ **Кэширование** для оптимизации
- 📝 **Подробное логирование** и мониторинг
- 🛡️ **Отказоустойчивость** и безопасность

Эта архитектура создает полноценную AI-платформу для логистики, которая автоматически обрабатывает запросы клиентов и предоставляет профессиональные рекомендации! 🚀
