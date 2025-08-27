"""
Qichacha сервис для проверки китайских поставщиков
"""

import asyncio
import hashlib
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime

import aiohttp
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class QichachaService:
    """Сервис для работы с Qichacha API"""
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://open.qichacha.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
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
            # Простой тест подключения
            test_result = await self.search_company("test")
            logger.info("Qichacha service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Qichacha service: {e}")
            raise
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Генерация подписи для API запроса"""
        # Сортируем параметры по ключу
        sorted_params = dict(sorted(params.items()))
        
        # Создаем строку для подписи
        sign_string = ""
        for key, value in sorted_params.items():
            sign_string += f"{key}{value}"
        
        # Добавляем секретный ключ
        sign_string += self.secret_key
        
        # Создаем MD5 хеш
        signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
        return signature
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Выполнение запроса к Qichacha API"""
        try:
            # Добавляем обязательные параметры
            params.update({
                "appKey": self.api_key,
                "timestamp": str(int(time.time() * 1000))
            })
            
            # Генерируем подпись
            signature = self._generate_signature(params)
            params["sign"] = signature
            
            url = f"{self.base_url}{endpoint}"
            
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Qichacha API request completed: {endpoint}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Qichacha API error: {response.status} - {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("Qichacha API request timeout")
            return None
        except Exception as e:
            logger.error(f"Qichacha API request failed: {e}")
            return None
    
    async def search_company(self, company_name: str) -> Dict[str, Any]:
        """Поиск компании по названию"""
        try:
            params = {
                "keyword": company_name,
                "pageIndex": "1",
                "pageSize": "10"
            }
            
            result = await self._make_request("/api/search/search", params)
            
            if result and result.get("Status") == "200":
                companies = result.get("Result", {}).get("List", [])
                
                if companies:
                    # Возвращаем первую найденную компанию
                    return {
                        "success": True,
                        "company": companies[0],
                        "total_count": result.get("Result", {}).get("TotalCount", 0)
                    }
                else:
                    return {
                        "success": False,
                        "error": "Company not found",
                        "message": f"No companies found for '{company_name}'"
                    }
            else:
                return {
                    "success": False,
                    "error": "API error",
                    "message": result.get("Message", "Unknown error") if result else "No response"
                }
                
        except Exception as e:
            logger.error(f"Error searching company: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_company_details(self, company_id: str) -> Dict[str, Any]:
        """Получение детальной информации о компании"""
        try:
            params = {
                "keyNo": company_id
            }
            
            result = await self._make_request("/api/company/getDetail", params)
            
            if result and result.get("Status") == "200":
                company_data = result.get("Result", {})
                
                return {
                    "success": True,
                    "company": company_data
                }
            else:
                return {
                    "success": False,
                    "error": "API error",
                    "message": result.get("Message", "Unknown error") if result else "No response"
                }
                
        except Exception as e:
            logger.error(f"Error getting company details: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_company_risk(self, company_id: str) -> Dict[str, Any]:
        """Проверка рисков компании"""
        try:
            params = {
                "keyNo": company_id
            }
            
            result = await self._make_request("/api/company/getRisk", params)
            
            if result and result.get("Status") == "200":
                risk_data = result.get("Result", {})
                
                return {
                    "success": True,
                    "risk_info": risk_data
                }
            else:
                return {
                    "success": False,
                    "error": "API error",
                    "message": result.get("Message", "Unknown error") if result else "No response"
                }
                
        except Exception as e:
            logger.error(f"Error checking company risk: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_company_financials(self, company_id: str) -> Dict[str, Any]:
        """Получение финансовой информации"""
        try:
            params = {
                "keyNo": company_id
            }
            
            result = await self._make_request("/api/company/getFinancial", params)
            
            if result and result.get("Status") == "200":
                financial_data = result.get("Result", {})
                
                return {
                    "success": True,
                    "financials": financial_data
                }
            else:
                return {
                    "success": False,
                    "error": "API error",
                    "message": result.get("Message", "Unknown error") if result else "No response"
                }
                
        except Exception as e:
            logger.error(f"Error getting company financials: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def comprehensive_supplier_check(self, company_name: str) -> Dict[str, Any]:
        """Комплексная проверка поставщика"""
        try:
            # 1. Поиск компании
            search_result = await self.search_company(company_name)
            
            if not search_result.get("success"):
                return search_result
            
            company = search_result["company"]
            company_id = company.get("KeyNo")
            
            if not company_id:
                return {
                    "success": False,
                    "error": "Company ID not found"
                }
            
            # 2. Получение детальной информации
            details_result = await self.get_company_details(company_id)
            
            # 3. Проверка рисков
            risk_result = await self.check_company_risk(company_id)
            
            # 4. Получение финансовой информации
            financial_result = await self.get_company_financials(company_id)
            
            # 5. Формирование комплексного отчета
            comprehensive_report = {
                "success": True,
                "company_name": company_name,
                "search_date": datetime.now().isoformat(),
                
                # Основная информация
                "basic_info": {
                    "name": company.get("Name"),
                    "registration_number": company.get("RegNumber"),
                    "legal_representative": company.get("LegalPersonName"),
                    "registered_capital": company.get("RegCapital"),
                    "establishment_date": company.get("EstablishTime"),
                    "business_status": company.get("Status"),
                    "industry": company.get("Industry"),
                    "address": company.get("Address")
                },
                
                # Детальная информация
                "details": details_result.get("company", {}) if details_result.get("success") else {},
                
                # Информация о рисках
                "risks": risk_result.get("risk_info", {}) if risk_result.get("success") else {},
                
                # Финансовая информация
                "financials": financial_result.get("financials", {}) if financial_result.get("success") else {},
                
                # Оценка надежности
                "reliability_score": self._calculate_reliability_score(
                    company, 
                    details_result.get("company", {}),
                    risk_result.get("risk_info", {}),
                    financial_result.get("financials", {})
                )
            }
            
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"Error in comprehensive supplier check: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_reliability_score(self, company: Dict, details: Dict, risks: Dict, financials: Dict) -> int:
        """Расчет оценки надежности поставщика (1-10)"""
        score = 5  # Базовая оценка
        
        try:
            # Проверка статуса компании
            status = company.get("Status", "").lower()
            if "active" in status or "正常" in status:
                score += 2
            elif "cancelled" in status or "吊销" in status:
                score -= 3
            
            # Проверка уставного капитала
            reg_capital = company.get("RegCapital", "")
            if reg_capital:
                try:
                    capital_value = float(reg_capital.replace("万", "").replace("万元", ""))
                    if capital_value > 1000:
                        score += 1
                    elif capital_value > 100:
                        score += 0.5
                except:
                    pass
            
            # Проверка даты регистрации
            establish_time = company.get("EstablishTime", "")
            if establish_time:
                try:
                    # Примерная проверка - компания старше 3 лет
                    if "2019" in establish_time or "2018" in establish_time:
                        score += 1
                except:
                    pass
            
            # Проверка рисков
            if risks:
                risk_count = len(risks.get("RiskList", []))
                if risk_count == 0:
                    score += 1
                elif risk_count <= 2:
                    score += 0.5
                else:
                    score -= min(risk_count - 2, 3)
            
            # Ограничиваем оценку от 1 до 10
            score = max(1, min(10, int(score)))
            
        except Exception as e:
            logger.error(f"Error calculating reliability score: {e}")
            score = 5
        
        return score


# Функция для получения экземпляра сервиса
async def get_qichacha_service() -> QichachaService:
    """Получение экземпляра Qichacha сервиса"""
    if not settings.QICHACHA_API_KEY or not settings.QICHACHA_SECRET_KEY:
        raise ValueError("QICHACHA_API_KEY and QICHACHA_SECRET_KEY not configured")
    
    service = QichachaService(settings.QICHACHA_API_KEY, settings.QICHACHA_SECRET_KEY)
    await service.initialize()
    return service

