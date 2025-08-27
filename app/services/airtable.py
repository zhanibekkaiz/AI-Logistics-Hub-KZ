"""
Сервис для работы с Airtable
Основное хранилище тарифов, клиентов и расчётов
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

import aiohttp
import structlog

from app.models.schemas import TariffInfo, DeliveryType
from app.core.config import settings

logger = structlog.get_logger(__name__)


class AirtableService:
    """Сервис для работы с Airtable API"""
    
    def __init__(self, api_key: str, base_id: str):
        self.api_key = api_key
        self.base_id = base_id
        self.base_url = f"https://api.airtable.com/v0/{base_id}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Названия таблиц
        self.tables = {
            "tariffs": "Tariffs",
            "clients": "Clients", 
            "calculations": "Calculations",
            "suppliers": "Suppliers",
            "orders": "Orders",
            "analytics": "Analytics"
        }
    
    async def initialize(self) -> None:
        """Инициализация сервиса - проверка подключения"""
        try:
            # Проверяем подключение, тестируя доступ к первой таблице
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/{self.tables['tariffs']}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        logger.info("Airtable connection established successfully")
                    else:
                        raise Exception(f"Airtable connection failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to initialize Airtable service: {e}")
            raise
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Выполнение HTTP запроса к Airtable API"""
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    timeout=30
                ) as response:
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Airtable API error: {response.status} - {error_text}"
                        )
                        raise Exception(f"Airtable API error: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error("Airtable API request timeout")
            raise Exception("Airtable API request timeout")
        except Exception as e:
            logger.error(f"Airtable API request failed: {e}")
            raise
    
    async def get_tariffs(
        self, 
        route: Optional[str] = None, 
        service_type: Optional[DeliveryType] = None
    ) -> List[TariffInfo]:
        """Получение тарифов с фильтрацией"""
        
        try:
            # Формируем фильтр
            filter_formula = ""
            if route:
                filter_formula += f"{{Route}} = '{route}'"
            if service_type:
                if filter_formula:
                    filter_formula += " AND "
                filter_formula += f"{{ServiceType}} = '{service_type.value}'"
            
            endpoint = f"{self.tables['tariffs']}"
            if filter_formula:
                endpoint += f"?filterByFormula={filter_formula}"
            
            response = await self._make_request("GET", endpoint)
            
            if not response:
                return []
            
            tariffs = []
            for record in response.get("records", []):
                fields = record.get("fields", {})
                
                tariff = TariffInfo(
                    route=fields.get("Route", ""),
                    service_type=DeliveryType(fields.get("ServiceType", "cargo")),
                    price_per_kg=Decimal(str(fields.get("PricePerKg", 0))),
                    transit_time_days=fields.get("TransitTimeDays", 0),
                    valid_from=datetime.fromisoformat(fields.get("ValidFrom", "2024-01-01")),
                    valid_to=datetime.fromisoformat(fields.get("ValidTo", "2024-12-31")) if fields.get("ValidTo") else None
                )
                tariffs.append(tariff)
            
            logger.info(f"Retrieved {len(tariffs)} tariffs")
            return tariffs
            
        except Exception as e:
            logger.error(f"Failed to get tariffs: {e}")
            raise
    
    async def get_available_routes(self) -> List[str]:
        """Получение списка доступных маршрутов"""
        
        try:
            response = await self._make_request("GET", f"{self.tables['tariffs']}")
            
            if not response:
                return []
            
            routes = set()
            for record in response.get("records", []):
                route = record.get("fields", {}).get("Route")
                if route:
                    routes.add(route)
            
            return sorted(list(routes))
            
        except Exception as e:
            logger.error(f"Failed to get available routes: {e}")
            raise
    
    async def get_route_tariffs(self, route: str) -> List[TariffInfo]:
        """Получение тарифов для конкретного маршрута"""
        
        return await self.get_tariffs(route=route)
    
    async def create_tariff(self, tariff: TariffInfo) -> TariffInfo:
        """Создание нового тарифа"""
        
        try:
            data = {
                "fields": {
                    "Route": tariff.route,
                    "ServiceType": tariff.service_type.value,
                    "PricePerKg": float(tariff.price_per_kg),
                    "TransitTimeDays": tariff.transit_time_days,
                    "ValidFrom": tariff.valid_from.isoformat(),
                    "ValidTo": tariff.valid_to.isoformat() if tariff.valid_to else None
                }
            }
            
            response = await self._make_request("POST", f"{self.tables['tariffs']}", data)
            
            if response and "records" in response:
                # Возвращаем созданный тариф
                return tariff
            
            raise Exception("Failed to create tariff")
            
        except Exception as e:
            logger.error(f"Failed to create tariff: {e}")
            raise
    
    async def update_tariff(self, tariff_id: str, tariff: TariffInfo) -> Optional[TariffInfo]:
        """Обновление тарифа"""
        
        try:
            data = {
                "fields": {
                    "Route": tariff.route,
                    "ServiceType": tariff.service_type.value,
                    "PricePerKg": float(tariff.price_per_kg),
                    "TransitTimeDays": tariff.transit_time_days,
                    "ValidFrom": tariff.valid_from.isoformat(),
                    "ValidTo": tariff.valid_to.isoformat() if tariff.valid_to else None
                }
            }
            
            response = await self._make_request("PATCH", f"{self.tables['tariffs']}/{tariff_id}", data)
            
            if response:
                return tariff
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to update tariff: {e}")
            raise
    
    async def delete_tariff(self, tariff_id: str) -> bool:
        """Удаление тарифа"""
        
        try:
            response = await self._make_request("DELETE", f"{self.tables['tariffs']}/{tariff_id}")
            return response is not None
            
        except Exception as e:
            logger.error(f"Failed to delete tariff: {e}")
            raise
    
    async def save_calculation(self, calculation_data: Dict[str, Any]) -> str:
        """Сохранение расчёта в Airtable"""
        
        try:
            data = {
                "fields": {
                    "RequestID": calculation_data.get("request_id"),
                    "Weight": float(calculation_data.get("weight", 0)),
                    "Volume": float(calculation_data.get("volume", 0)),
                    "Category": calculation_data.get("category"),
                    "Origin": calculation_data.get("origin"),
                    "Destination": calculation_data.get("destination"),
                    "CargoCost": float(calculation_data.get("cargo_cost", 0)),
                    "WhiteCost": float(calculation_data.get("white_cost", 0)),
                    "CalculationDate": datetime.now().isoformat(),
                    "Status": "completed"
                }
            }
            
            response = await self._make_request("POST", f"{self.tables['calculations']}", data)
            
            if response and "records" in response:
                record_id = response["records"][0]["id"]
                logger.info(f"Calculation saved with ID: {record_id}")
                return record_id
            
            raise Exception("Failed to save calculation")
            
        except Exception as e:
            logger.error(f"Failed to save calculation: {e}")
            raise
    
    async def get_calculation_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Получение расчёта по ID"""
        
        try:
            filter_formula = f"{{RequestID}} = '{request_id}'"
            endpoint = f"{self.tables['calculations']}?filterByFormula={filter_formula}"
            
            response = await self._make_request("GET", endpoint)
            
            if response and "records" in response and response["records"]:
                return response["records"][0]["fields"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get calculation: {e}")
            raise
    
    async def get_user_calculation_history(
        self, 
        user_id: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получение истории расчётов пользователя"""
        
        try:
            # TODO: Добавить фильтрацию по user_id когда будет аутентификация
            endpoint = f"{self.tables['calculations']}?pageSize={limit}"
            
            response = await self._make_request("GET", endpoint)
            
            if not response:
                return []
            
            calculations = []
            for record in response.get("records", []):
                calculations.append(record["fields"])
            
            return calculations[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Failed to get calculation history: {e}")
            raise
    
    async def save_client(self, client_data: Dict[str, Any]) -> str:
        """Сохранение клиента в Airtable"""
        
        try:
            data = {
                "fields": {
                    "Name": client_data.get("name"),
                    "Email": client_data.get("email"),
                    "Phone": client_data.get("phone"),
                    "Company": client_data.get("company"),
                    "TelegramID": client_data.get("telegram_id"),
                    "RegistrationDate": datetime.now().isoformat(),
                    "Status": "active"
                }
            }
            
            response = await self._make_request("POST", f"{self.tables['clients']}", data)
            
            if response and "records" in response:
                record_id = response["records"][0]["id"]
                logger.info(f"Client saved with ID: {record_id}")
                return record_id
            
            raise Exception("Failed to save client")
            
        except Exception as e:
            logger.error(f"Failed to save client: {e}")
            raise

    # ===== НОВЫЕ МЕТОДЫ ДЛЯ ТАБЛИЦЫ ORDERS =====
    
    async def save_order(self, order_data: Dict[str, Any]) -> str:
        """Сохранение заказа в Airtable"""
        
        try:
            data = {
                "fields": {
                    "ClientName": order_data.get("client_name"),
                    "Product": order_data.get("product"),
                    "Weight": float(order_data.get("weight", 0)),
                    "Volume": float(order_data.get("volume", 0)),
                    "Origin": order_data.get("origin"),
                    "Destination": order_data.get("destination"),
                    "TNVEDCode": order_data.get("tnved_code"),
                    "Status": order_data.get("status", "new"),
                    "OrderDate": datetime.now().isoformat(),
                    "Notes": order_data.get("notes", "")
                }
            }
            
            response = await self._make_request("POST", f"{self.tables['orders']}", data)
            
            if response and "records" in response:
                record_id = response["records"][0]["id"]
                logger.info(f"Order saved with ID: {record_id}")
                return record_id
            
            raise Exception("Failed to save order")
            
        except Exception as e:
            logger.error(f"Failed to save order: {e}")
            raise
    
    async def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Получение заказа по ID"""
        
        try:
            response = await self._make_request("GET", f"{self.tables['orders']}/{order_id}")
            
            if response and "fields" in response:
                return response["fields"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get order: {e}")
            raise
    
    async def update_order_status(self, order_id: str, status: str) -> bool:
        """Обновление статуса заказа"""
        
        try:
            data = {
                "fields": {
                    "Status": status
                }
            }
            
            response = await self._make_request("PATCH", f"{self.tables['orders']}/{order_id}", data)
            
            return response is not None
            
        except Exception as e:
            logger.error(f"Failed to update order status: {e}")
            raise
    
    async def get_orders_by_client(self, client_name: str) -> List[Dict[str, Any]]:
        """Получение заказов клиента"""
        
        try:
            filter_formula = f"{{ClientName}} = '{client_name}'"
            endpoint = f"{self.tables['orders']}?filterByFormula={filter_formula}"
            
            response = await self._make_request("GET", endpoint)
            
            if not response:
                return []
            
            orders = []
            for record in response.get("records", []):
                orders.append(record["fields"])
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get client orders: {e}")
            raise

    # ===== НОВЫЕ МЕТОДЫ ДЛЯ ТАБЛИЦЫ ANALYTICS =====
    
    async def save_analytics(self, analytics_data: Dict[str, Any]) -> str:
        """Сохранение аналитики в Airtable"""
        
        try:
            data = {
                "fields": {
                    "Date": analytics_data.get("date", datetime.now().isoformat()),
                    "TotalOrders": int(analytics_data.get("total_orders", 0)),
                    "TotalRevenue": float(analytics_data.get("total_revenue", 0)),
                    "CargoOrders": int(analytics_data.get("cargo_orders", 0)),
                    "WhiteOrders": int(analytics_data.get("white_orders", 0)),
                    "NewClients": int(analytics_data.get("new_clients", 0)),
                    "ConversionRate": float(analytics_data.get("conversion_rate", 0)),
                    "AvgOrderValue": float(analytics_data.get("avg_order_value", 0)),
                    "TotalWeight": float(analytics_data.get("total_weight", 0)),
                    "TotalVolume": float(analytics_data.get("total_volume", 0)),
                    "TopOrigin": analytics_data.get("top_origin", ""),
                    "TopDestination": analytics_data.get("top_destination", ""),
                    "Notes": analytics_data.get("notes", "")
                }
            }
            
            response = await self._make_request("POST", f"{self.tables['analytics']}", data)
            
            if response and "records" in response:
                record_id = response["records"][0]["id"]
                logger.info(f"Analytics saved with ID: {record_id}")
                return record_id
            
            raise Exception("Failed to save analytics")
            
        except Exception as e:
            logger.error(f"Failed to save analytics: {e}")
            raise
    
    async def get_daily_analytics(self, date: str) -> Optional[Dict[str, Any]]:
        """Получение аналитики за конкретную дату"""
        
        try:
            filter_formula = f"{{Date}} = '{date}'"
            endpoint = f"{self.tables['analytics']}?filterByFormula={filter_formula}"
            
            response = await self._make_request("GET", endpoint)
            
            if response and "records" in response and response["records"]:
                return response["records"][0]["fields"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get daily analytics: {e}")
            raise
    
    async def get_analytics_period(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Получение аналитики за период"""
        
        try:
            filter_formula = f"AND({{Date}} >= '{start_date}', {{Date}} <= '{end_date}')"
            endpoint = f"{self.tables['analytics']}?filterByFormula={filter_formula}"
            
            response = await self._make_request("GET", endpoint)
            
            if not response:
                return []
            
            analytics = []
            for record in response.get("records", []):
                analytics.append(record["fields"])
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get analytics period: {e}")
            raise

    # ===== НОВЫЕ МЕТОДЫ ДЛЯ ТАБЛИЦЫ SUPPLIERS =====
    
    async def save_supplier(self, supplier_data: Dict[str, Any]) -> str:
        """Сохранение поставщика в Airtable"""
        
        try:
            data = {
                "fields": {
                    "CompanyName": supplier_data.get("company_name"),
                    "ContactPerson": supplier_data.get("contact_person"),
                    "Email": supplier_data.get("email"),
                    "Phone": supplier_data.get("phone"),
                    "Address": supplier_data.get("address"),
                    "Specialization": supplier_data.get("specialization"),
                    "Rating": int(supplier_data.get("rating", 0)),
                    "Status": supplier_data.get("status", "active"),
                    "RegistrationDate": supplier_data.get("registration_date", datetime.now().isoformat()),
                    "Website": supplier_data.get("website", ""),
                    "Notes": supplier_data.get("notes", ""),
                    "LastContactDate": supplier_data.get("last_contact_date", datetime.now().isoformat())
                }
            }
            
            response = await self._make_request("POST", f"{self.tables['suppliers']}", data)
            
            if response and "records" in response:
                record_id = response["records"][0]["id"]
                logger.info(f"Supplier saved with ID: {record_id}")
                return record_id
            
            raise Exception("Failed to save supplier")
            
        except Exception as e:
            logger.error(f"Failed to save supplier: {e}")
            raise
    
    async def get_suppliers_by_specialization(self, specialization: str) -> List[Dict[str, Any]]:
        """Получение поставщиков по специализации"""
        
        try:
            filter_formula = f"{{Specialization}} = '{specialization}'"
            endpoint = f"{self.tables['suppliers']}?filterByFormula={filter_formula}"
            
            response = await self._make_request("GET", endpoint)
            
            if not response:
                return []
            
            suppliers = []
            for record in response.get("records", []):
                suppliers.append(record["fields"])
            
            return suppliers
            
        except Exception as e:
            logger.error(f"Failed to get suppliers by specialization: {e}")
            raise
    
    async def update_supplier_rating(self, supplier_id: str, rating: int) -> bool:
        """Обновление рейтинга поставщика"""
        
        try:
            data = {
                "fields": {
                    "Rating": rating
                }
            }
            
            response = await self._make_request("PATCH", f"{self.tables['suppliers']}/{supplier_id}", data)
            
            return response is not None
            
        except Exception as e:
            logger.error(f"Failed to update supplier rating: {e}")
            raise

    # ===== МЕТОДЫ ДЛЯ АВТОМАТИЧЕСКОЙ СВЯЗИ ТАБЛИЦ =====
    
    async def create_order_with_calculation(
        self, 
        order_data: Dict[str, Any], 
        calculation_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Создание заказа с автоматическим созданием расчета"""
        
        try:
            # Создаем заказ
            order_id = await self.save_order(order_data)
            
            # Добавляем OrderID в данные расчета
            calculation_data["OrderID"] = order_id
            
            # Создаем расчет
            calculation_id = await self.save_calculation(calculation_data)
            
            logger.info(f"Created order {order_id} with calculation {calculation_id}")
            
            return {
                "order_id": order_id,
                "calculation_id": calculation_id
            }
            
        except Exception as e:
            logger.error(f"Failed to create order with calculation: {e}")
            raise
    
    async def get_order_with_calculation(self, order_id: str) -> Dict[str, Any]:
        """Получение заказа с его расчетом"""
        
        try:
            # Получаем заказ
            order = await self.get_order_by_id(order_id)
            if not order:
                return {}
            
            # Получаем расчет по OrderID
            calculation = await self.get_calculation_by_id(order_id)
            
            return {
                "order": order,
                "calculation": calculation
            }
            
        except Exception as e:
            logger.error(f"Failed to get order with calculation: {e}")
            raise
