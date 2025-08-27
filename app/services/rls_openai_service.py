"""
OpenAI сервис для AI Logistics Hub
Интерпретация данных ТН ВЭД, анализ поставщиков, генерация отчетов
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import aiohttp
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class OpenAIService:
    """Сервис для работы с OpenAI API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        self.model = "gpt-4o-mini"  # Используем более доступную модель
        
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.session:
            await self.session.close()
    
    async def initialize(self) -> None:
        """Инициализация сервиса"""
        try:
            # Проверяем подключение к OpenAI API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Простой тест подключения
            async with self.session.get(f"{self.base_url}/models", headers=headers) as response:
                if response.status == 200:
                    models = await response.json()
                    logger.info(f"OpenAI service initialized. Available models: {len(models.get('data', []))}")
                else:
                    raise Exception(f"Failed to initialize OpenAI service: {response.status}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {e}")
            raise
    
    async def _make_request(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> Optional[str]:
        """Выполнение запроса к OpenAI API"""
        try:
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"OpenAI request completed successfully")
                    return content
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {response.status} - {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("OpenAI API request timeout")
            return None
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            return None
    
    async def interpret_tnved_data(self, tnved_data: Dict[str, Any]) -> Dict[str, Any]:
        """Интерпретация данных ТН ВЭД с помощью AI"""
        try:
            prompt = f"""
Проанализируйте данные ТН ВЭД и предоставьте структурированный отчет на русском языке.

Данные ТН ВЭД:
{json.dumps(tnved_data, ensure_ascii=False, indent=2)}

Предоставьте анализ в следующем формате:
1. Описание товара и его назначение
2. Ставки пошлин и НДС для Казахстана
3. Требуемые документы для импорта
4. Ограничения и особенности
5. Рекомендации по таможенному оформлению

Ответ должен быть структурированным и понятным для клиента.
            """
            
            messages = [
                {"role": "system", "content": "Вы - эксперт по таможенному оформлению и логистике. Анализируете ТН ВЭД коды и даете рекомендации по импорту товаров в Казахстан."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._make_request(messages, max_tokens=1500)
            
            if response:
                return {
                    "success": True,
                    "interpretation": response,
                    "timestamp": datetime.now().isoformat(),
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to get AI interpretation",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error interpreting TNVED data: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def analyze_supplier_report(self, supplier_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ отчета о поставщике с помощью AI"""
        try:
            prompt = f"""
Проанализируйте данные о китайском поставщике и предоставьте оценку надежности.

Данные поставщика:
{json.dumps(supplier_data, ensure_ascii=False, indent=2)}

Предоставьте анализ в следующем формате:
1. Общая оценка надежности (1-10)
2. Анализ рисков
3. Рекомендации по работе с поставщиком
4. Требуемые проверки
5. Альтернативные варианты (если есть риски)

Ответ должен быть структурированным и содержать конкретные рекомендации.
            """
            
            messages = [
                {"role": "system", "content": "Вы - эксперт по проверке китайских поставщиков. Анализируете данные компаний и даете рекомендации по надежности и рискам."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._make_request(messages, max_tokens=1500)
            
            if response:
                return {
                    "success": True,
                    "analysis": response,
                    "timestamp": datetime.now().isoformat(),
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to get AI analysis",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error analyzing supplier report: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def calculate_logistics(self, order_data: Dict[str, Any], tariffs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Расчет логистики с помощью AI"""
        try:
            prompt = f"""
Рассчитайте стоимость доставки и предоставьте рекомендации по логистике.

Данные заказа:
{json.dumps(order_data, ensure_ascii=False, indent=2)}

Доступные тарифы:
{json.dumps(tariffs, ensure_ascii=False, indent=2)}

Предоставьте расчет в следующем формате:
1. Расчет стоимости карго доставки
2. Расчет стоимости белой доставки
3. Сравнение вариантов
4. Рекомендации по выбору
5. Дополнительные расходы
6. Время в пути и риски

Ответ должен содержать конкретные цифры и обоснованные рекомендации.
            """
            
            messages = [
                {"role": "system", "content": "Вы - эксперт по международной логистике. Рассчитываете стоимость доставки и даете рекомендации по выбору оптимального варианта."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._make_request(messages, max_tokens=2000)
            
            if response:
                return {
                    "success": True,
                    "calculation": response,
                    "timestamp": datetime.now().isoformat(),
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to get AI calculation",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error calculating logistics: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def generate_comprehensive_report(
        self, 
        order_data: Dict[str, Any],
        tnved_data: Dict[str, Any],
        supplier_data: Dict[str, Any],
        logistics_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Генерация комплексного отчета"""
        try:
            prompt = f"""
Создайте комплексный отчет по заказу, включающий все аспекты: таможенное оформление, логистику и проверку поставщика.

Данные заказа:
{json.dumps(order_data, ensure_ascii=False, indent=2)}

Данные ТН ВЭД:
{json.dumps(tnved_data, ensure_ascii=False, indent=2)}

Данные поставщика:
{json.dumps(supplier_data, ensure_ascii=False, indent=2)}

Данные логистики:
{json.dumps(logistics_data, ensure_ascii=False, indent=2)}

Создайте структурированный отчет:
1. Краткое резюме заказа
2. Таможенное оформление (ТН ВЭД, документы, пошлины)
3. Логистика (варианты доставки, стоимость, время)
4. Поставщик (надежность, риски, рекомендации)
5. Общие рекомендации и план действий
6. Контакты для консультаций

Отчет должен быть профессиональным и понятным для клиента.
            """
            
            messages = [
                {"role": "system", "content": "Вы - эксперт по международной торговле и логистике. Создаете комплексные отчеты для клиентов по импорту товаров из Китая в Казахстан."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._make_request(messages, max_tokens=3000)
            
            if response:
                return {
                    "success": True,
                    "report": response,
                    "timestamp": datetime.now().isoformat(),
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to generate report",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error generating comprehensive report: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_cost_estimate(self, text: str) -> Dict[str, Any]:
        """Получение примерной оценки стоимости по текстовому описанию"""
        try:
            prompt = f"""
Оцените примерную стоимость доставки на основе описания товара.

Описание: {text}

Предоставьте оценку в формате:
1. Примерный вес и объем
2. Стоимость карго доставки
3. Стоимость белой доставки
4. Время в пути
5. Дополнительные расходы

Укажите, что это предварительная оценка и точный расчет требует детальных данных.
            """
            
            messages = [
                {"role": "system", "content": "Вы - эксперт по логистике. Даете предварительные оценки стоимости доставки на основе описания товаров."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._make_request(messages, max_tokens=1000)
            
            if response:
                return {
                    "success": True,
                    "estimate": response,
                    "timestamp": datetime.now().isoformat(),
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to get cost estimate",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting cost estimate: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Функция для получения экземпляра сервиса
async def get_openai_service() -> OpenAIService:
    """Получение экземпляра OpenAI сервиса"""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    
    service = OpenAIService(settings.OPENAI_API_KEY)
    await service.initialize()
    return service
