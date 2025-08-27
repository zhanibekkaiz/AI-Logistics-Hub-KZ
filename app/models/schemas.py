"""
Pydantic схемы для валидации данных AI Logistics Hub
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator, model_validator


class DeliveryType(str, Enum):
    """Типы доставки"""
    CARGO = "cargo"
    WHITE = "white"


class CargoCategory(str, Enum):
    """Категории грузов"""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    MACHINERY = "machinery"
    CHEMICALS = "chemicals"
    FOOD = "food"
    OTHER = "other"


class CalculationRequest(BaseModel):
    """Схема запроса на расчёт доставки"""
    
    weight: Decimal = Field(..., gt=0, description="Вес груза в кг")
    volume: Decimal = Field(..., gt=0, description="Объём груза в м³")
    category: CargoCategory = Field(..., description="Категория товара")
    origin: str = Field(..., min_length=2, max_length=100, description="Город отправления")
    destination: str = Field(..., min_length=2, max_length=100, description="Город назначения")
    description: Optional[str] = Field(None, max_length=500, description="Описание товара")
    
    @field_validator('weight', 'volume')
    @classmethod
    def validate_positive_decimal(cls, v):
        """Проверка положительного значения"""
        if v <= 0:
            raise ValueError('Значение должно быть больше нуля')
        return v
    
    @model_validator(mode='after')
    def validate_origin_destination(self):
        """Проверка, что города отправления и назначения разные"""
        if self.origin and self.destination and self.origin.lower() == self.destination.lower():
            raise ValueError('Город отправления и назначения не могут быть одинаковыми')
        
        return self
    
    class Config:
        schema_extra = {
            "example": {
                "weight": 100.5,
                "volume": 0.5,
                "category": "electronics",
                "origin": "Shenzhen",
                "destination": "Almaty",
                "description": "LED light bulbs, 10W, E27 base"
            }
        }


class TNVEDRequest(BaseModel):
    """Схема запроса на определение ТН ВЭД"""
    
    description: str = Field(..., min_length=10, max_length=1000, description="Описание товара")
    category: Optional[CargoCategory] = Field(None, description="Категория товара")
    
    class Config:
        schema_extra = {
            "example": {
                "description": "LED light bulbs, 10W, E27 base, white color, energy efficient",
                "category": "electronics"
            }
        }


class TNVEDSearchRequest(BaseModel):
    """Схема запроса на поиск ТН ВЭД кодов"""
    
    query: str = Field(..., min_length=2, max_length=500, description="Поисковый запрос")
    group: Optional[str] = Field(None, max_length=10, description="Фильтр по группам (например, '0704')")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "LED light bulbs",
                "group": "8539"
            }
        }


class TNVEDSearchResult(BaseModel):
    """Результат поиска ТН ВЭД кода"""
    
    probability: float = Field(..., description="Вероятность совпадения")
    code: str = Field(..., description="Код ТН ВЭД")
    description: str = Field(..., description="Описание кода")
    start_date: Optional[datetime] = Field(None, description="Дата начала действия кода")
    end_date: Optional[datetime] = Field(None, description="Дата окончания действия кода")
    is_old: bool = Field(False, description="Показатель того, устарел ли код")
    
    class Config:
        schema_extra = {
            "example": {
                "probability": 96.28,
                "code": "8539310000",
                "description": "ЛАМПЫ СВЕТОДИОДНЫЕ",
                "start_date": "2017-01-01T00:00:00Z",
                "end_date": None,
                "is_old": False
            }
        }


class TNVEDLicenseInfo(BaseModel):
    """Информация о лицензии TNVED API"""
    
    work_place: str = Field(..., description="Номер рабочего места")
    end_date: Optional[datetime] = Field(None, description="Дата окончания действия лицензии")
    remain: int = Field(..., description="Осталось использований")
    total: int = Field(..., description="Всего использований")
    
    class Config:
        schema_extra = {
            "example": {
                "work_place": "91036",
                "end_date": "2024-12-31T00:00:00Z",
                "remain": 2947,
                "total": 3000
            }
        }


class TNVEDSearchResponse(BaseModel):
    """Ответ на поиск ТН ВЭД кодов"""
    
    success: bool = Field(..., description="Успешность запроса")
    results: List[TNVEDSearchResult] = Field(default_factory=list, description="Результаты поиска")
    license_info: Optional[TNVEDLicenseInfo] = Field(None, description="Информация о лицензии")
    response_state: int = Field(..., description="Состояние запроса")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "results": [
                    {
                        "probability": 96.28,
                        "code": "8539310000",
                        "description": "ЛАМПЫ СВЕТОДИОДНЫЕ",
                        "start_date": "2017-01-01T00:00:00Z",
                        "end_date": None,
                        "is_old": False
                    }
                ],
                "license_info": {
                    "work_place": "91036",
                    "end_date": "2024-12-31T00:00:00Z",
                    "remain": 2947,
                    "total": 3000
                },
                "response_state": 200,
                "error_message": None
            }
        }


class SupplierCheckRequest(BaseModel):
    """Схема запроса на проверку поставщика"""
    
    company_name: str = Field(..., min_length=2, max_length=200, description="Название компании")
    registration_number: Optional[str] = Field(None, max_length=50, description="Регистрационный номер")
    country: str = Field(default="China", max_length=50, description="Страна регистрации")
    
    class Config:
        schema_extra = {
            "example": {
                "company_name": "Shenzhen Electronics Co., Ltd.",
                "registration_number": "91440300XXXXXXXXXX",
                "country": "China"
            }
        }


class TariffInfo(BaseModel):
    """Информация о тарифе"""
    
    route: str = Field(..., description="Маршрут")
    service_type: DeliveryType = Field(..., description="Тип услуги")
    price_per_kg: Decimal = Field(..., description="Цена за кг")
    transit_time_days: int = Field(..., description="Время в пути в днях")
    valid_from: datetime = Field(..., description="Дата начала действия")
    valid_to: Optional[datetime] = Field(None, description="Дата окончания действия")
    
    class Config:
        schema_extra = {
            "example": {
                "route": "shenzhen-almaty",
                "service_type": "cargo",
                "price_per_kg": 2.50,
                "transit_time_days": 10,
                "valid_from": "2024-01-01T00:00:00Z"
            }
        }


class TNVEDInfo(BaseModel):
    """Информация о ТН ВЭД"""
    
    code: str = Field(..., description="Код ТН ВЭД")
    description: str = Field(..., description="Описание товара")
    duty_rate: Optional[Decimal] = Field(None, description="Ставка пошлины (%)")
    vat_rate: Optional[Decimal] = Field(None, description="Ставка НДС (%)")
    required_documents: List[str] = Field(default_factory=list, description="Требуемые документы")
    restrictions: List[str] = Field(default_factory=list, description="Ограничения")
    
    class Config:
        schema_extra = {
            "example": {
                "code": "8539.31.000.0",
                "description": "Лампы светодиодные",
                "duty_rate": 5.0,
                "vat_rate": 12.0,
                "required_documents": ["Сертификат соответствия", "Декларация соответствия"],
                "restrictions": []
            }
        }


class SupplierInfo(BaseModel):
    """Информация о поставщике"""
    
    company_name: str = Field(..., description="Название компании")
    registration_number: Optional[str] = Field(None, description="Регистрационный номер")
    registration_date: Optional[datetime] = Field(None, description="Дата регистрации")
    capital: Optional[Decimal] = Field(None, description="Уставной капитал")
    licenses: List[str] = Field(default_factory=list, description="Лицензии")
    court_cases: int = Field(default=0, description="Количество судебных дел")
    export_history: Optional[str] = Field(None, description="История экспорта")
    reliability_score: int = Field(..., ge=0, le=100, description="Оценка надёжности (0-100)")
    risk_level: str = Field(..., description="Уровень риска")
    
    class Config:
        schema_extra = {
            "example": {
                "company_name": "Shenzhen Electronics Co., Ltd.",
                "registration_number": "91440300XXXXXXXXXX",
                "registration_date": "2012-05-15T00:00:00Z",
                "capital": 30000000,
                "licenses": ["Business License", "Export License"],
                "court_cases": 0,
                "export_history": "Экспортирует в ЕС и США с 2015 года",
                "reliability_score": 85,
                "risk_level": "low"
            }
        }


class CalculationResult(BaseModel):
    """Результат расчёта доставки"""
    
    request_id: str = Field(..., description="ID запроса")
    calculation_date: datetime = Field(..., description="Дата расчёта")
    
    # Исходные данные
    weight: Decimal = Field(..., description="Вес груза в кг")
    volume: Decimal = Field(..., description="Объём груза в м³")
    category: CargoCategory = Field(..., description="Категория товара")
    origin: str = Field(..., description="Город отправления")
    destination: str = Field(..., description="Город назначения")
    
    # Результаты расчёта
    cargo_delivery: Dict[str, Any] = Field(..., description="Карго доставка")
    white_delivery: Dict[str, Any] = Field(..., description="Белая доставка")
    
    # Дополнительная информация
    tnved_info: Optional[TNVEDInfo] = Field(None, description="Информация о ТН ВЭД")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "calc_123456",
                "calculation_date": "2024-01-01T12:00:00Z",
                "weight": 100.5,
                "volume": 0.5,
                "category": "electronics",
                "origin": "Shenzhen",
                "destination": "Almaty",
                "cargo_delivery": {
                    "total_cost": 251.25,
                    "transit_time": 10,
                    "risk_level": "medium"
                },
                "white_delivery": {
                    "total_cost": 450.75,
                    "transit_time": 20,
                    "risk_level": "low"
                },
                "recommendations": [
                    "Рекомендуем белую доставку для снижения рисков",
                    "Необходим сертификат соответствия"
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Схема ответа с ошибкой"""
    
    error: str = Field(..., description="Тип ошибки")
    message: str = Field(..., description="Сообщение об ошибке")
    details: Optional[Dict[str, Any]] = Field(None, description="Детали ошибки")
    request_id: Optional[str] = Field(None, description="ID запроса")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Неверные данные запроса",
                "details": {
                    "field": "weight",
                    "issue": "Значение должно быть больше нуля"
                },
                "request_id": "req_123456"
            }
        }


class SuccessResponse(BaseModel):
    """Схема успешного ответа"""
    
    success: bool = Field(True, description="Статус успеха")
    message: str = Field(..., description="Сообщение")
    data: Optional[Dict[str, Any]] = Field(None, description="Данные ответа")
    request_id: Optional[str] = Field(None, description="ID запроса")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Расчёт выполнен успешно",
                "data": {
                    "calculation_id": "calc_123456"
                },
                "request_id": "req_123456"
            }
        }
