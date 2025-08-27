"""
Сервис расчётов доставки
Основная бизнес-логика MVP
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional

import structlog

from app.models.schemas import (
    CalculationRequest,
    CalculationResult,
    TNVEDInfo,
    DeliveryType
)
from app.services.airtable import AirtableService
from app.services.tnved import TNVEDService

logger = structlog.get_logger(__name__)


class CalculationService:
    """Сервис для расчёта стоимости доставки"""
    
    def __init__(self, airtable_service: AirtableService, tnved_service: TNVEDService):
        self.airtable_service = airtable_service
        self.tnved_service = tnved_service
        
        # Коэффициенты для разных типов доставки
        self.delivery_coefficients = {
            DeliveryType.CARGO: {
                "base_multiplier": 1.0,
                "volume_multiplier": 1.2,  # Учитываем объём
                "category_multipliers": {
                    "electronics": 1.1,
                    "clothing": 0.9,
                    "machinery": 1.3,
                    "chemicals": 1.5,
                    "food": 1.2,
                    "other": 1.0
                }
            },
            DeliveryType.WHITE: {
                "base_multiplier": 1.8,  # Белая доставка дороже
                "volume_multiplier": 1.1,
                "category_multipliers": {
                    "electronics": 1.2,
                    "clothing": 1.0,
                    "machinery": 1.4,
                    "chemicals": 1.6,
                    "food": 1.3,
                    "other": 1.1
                }
            }
        }
    
    async def calculate_delivery(
        self, 
        request: CalculationRequest, 
        request_id: str
    ) -> CalculationResult:
        """
        Основной метод расчёта доставки
        
        Выполняет:
        1. Получение тарифов из Airtable
        2. Определение ТН ВЭД кода
        3. Расчёт стоимости для карго и белой доставки
        4. Генерация рекомендаций
        """
        
        try:
            logger.info(
                "Starting delivery calculation",
                request_id=request_id,
                weight=float(request.weight),
                volume=float(request.volume)
            )
            
            # 1. Получаем тарифы для маршрута
            route = f"{request.origin.lower()}-{request.destination.lower()}"
            tariffs = await self.airtable_service.get_tariffs(route=route)
            
            if not tariffs:
                # Если тарифы не найдены, используем базовые
                tariffs = self._get_default_tariffs(route)
                logger.warning(
                    "No tariffs found, using default tariffs",
                    request_id=request_id,
                    route=route
                )
            
            # 2. Определяем ТН ВЭД код
            tnved_info = None
            if request.description:
                tnved_info = await self.tnved_service.classify_product(
                    description=request.description,
                    category=request.category,
                    request_id=request_id
                )
            
            # 3. Рассчитываем стоимость для каждого типа доставки
            cargo_delivery = await self._calculate_cargo_delivery(
                request=request,
                tariffs=tariffs,
                tnved_info=tnved_info
            )
            
            white_delivery = await self._calculate_white_delivery(
                request=request,
                tariffs=tariffs,
                tnved_info=tnved_info
            )
            
            # 4. Генерируем рекомендации
            recommendations = self._generate_recommendations(
                request=request,
                cargo_delivery=cargo_delivery,
                white_delivery=white_delivery,
                tnved_info=tnved_info
            )
            
            # 5. Создаём результат
            result = CalculationResult(
                request_id=request_id,
                calculation_date=datetime.now(),
                weight=request.weight,
                volume=request.volume,
                category=request.category,
                origin=request.origin,
                destination=request.destination,
                cargo_delivery=cargo_delivery,
                white_delivery=white_delivery,
                tnved_info=tnved_info,
                recommendations=recommendations
            )
            
            # 6. Сохраняем расчёт в Airtable
            await self._save_calculation(request_id, request, result)
            
            logger.info(
                "Delivery calculation completed",
                request_id=request_id,
                cargo_cost=cargo_delivery.get("total_cost"),
                white_cost=white_delivery.get("total_cost")
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Delivery calculation failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _calculate_cargo_delivery(
        self,
        request: CalculationRequest,
        tariffs: List,
        tnved_info: Optional[TNVEDInfo]
    ) -> Dict[str, Any]:
        """Расчёт стоимости карго доставки"""
        
        # Находим подходящий тариф
        cargo_tariff = self._find_best_tariff(tariffs, DeliveryType.CARGO, request.weight)
        
        if not cargo_tariff:
            # Используем базовый тариф
            base_price_per_kg = Decimal("2.50")
            transit_time = 10
        else:
            base_price_per_kg = cargo_tariff.price_per_kg
            transit_time = cargo_tariff.transit_time_days
        
        # Применяем коэффициенты
        category_multiplier = self.delivery_coefficients[DeliveryType.CARGO]["category_multipliers"].get(
            request.category.value, 1.0
        )
        
        # Учитываем объём
        volume_weight = request.volume * 167  # 1 м³ = 167 кг
        chargeable_weight = max(request.weight, volume_weight)
        
        # Рассчитываем стоимость
        base_cost = base_price_per_kg * chargeable_weight
        adjusted_cost = base_cost * Decimal(str(category_multiplier))
        
        # Добавляем дополнительные услуги
        additional_services = self._calculate_additional_services(
            request=request,
            delivery_type=DeliveryType.CARGO,
            tnved_info=tnved_info
        )
        
        total_cost = adjusted_cost + additional_services["total"]
        
        return {
            "total_cost": float(total_cost),
            "base_cost": float(base_cost),
            "additional_services": additional_services,
            "transit_time": transit_time,
            "risk_level": "medium",
            "chargeable_weight": float(chargeable_weight),
            "price_per_kg": float(base_price_per_kg)
        }
    
    async def _calculate_white_delivery(
        self,
        request: CalculationRequest,
        tariffs: List,
        tnved_info: Optional[TNVEDInfo]
    ) -> Dict[str, Any]:
        """Расчёт стоимости белой доставки"""
        
        # Находим подходящий тариф
        white_tariff = self._find_best_tariff(tariffs, DeliveryType.WHITE, request.weight)
        
        if not white_tariff:
            # Используем базовый тариф
            base_price_per_kg = Decimal("4.50")
            transit_time = 20
        else:
            base_price_per_kg = white_tariff.price_per_kg
            transit_time = white_tariff.transit_time_days
        
        # Применяем коэффициенты
        category_multiplier = self.delivery_coefficients[DeliveryType.WHITE]["category_multipliers"].get(
            request.category.value, 1.0
        )
        
        # Учитываем объём
        volume_weight = request.volume * 167
        chargeable_weight = max(request.weight, volume_weight)
        
        # Рассчитываем стоимость
        base_cost = base_price_per_kg * chargeable_weight
        adjusted_cost = base_cost * Decimal(str(category_multiplier))
        
        # Добавляем таможенные услуги
        customs_services = self._calculate_customs_services(
            request=request,
            tnved_info=tnved_info
        )
        
        # Добавляем дополнительные услуги
        additional_services = self._calculate_additional_services(
            request=request,
            delivery_type=DeliveryType.WHITE,
            tnved_info=tnved_info
        )
        
        total_cost = adjusted_cost + customs_services["total"] + additional_services["total"]
        
        return {
            "total_cost": float(total_cost),
            "base_cost": float(base_cost),
            "customs_services": customs_services,
            "additional_services": additional_services,
            "transit_time": transit_time,
            "risk_level": "low",
            "chargeable_weight": float(chargeable_weight),
            "price_per_kg": float(base_price_per_kg)
        }
    
    def _find_best_tariff(
        self, 
        tariffs: List, 
        delivery_type: DeliveryType, 
        weight: Decimal
    ) -> Optional:
        """Поиск лучшего тарифа для заданных параметров"""
        
        suitable_tariffs = [
            t for t in tariffs 
            if t.service_type == delivery_type
        ]
        
        if not suitable_tariffs:
            return None
        
        # Сортируем по цене и выбираем самый подходящий
        suitable_tariffs.sort(key=lambda x: x.price_per_kg)
        return suitable_tariffs[0]
    
    def _calculate_customs_services(
        self,
        request: CalculationRequest,
        tnved_info: Optional[TNVEDInfo]
    ) -> Dict[str, Any]:
        """Расчёт таможенных услуг"""
        
        services = {
            "customs_clearance": 50.0,  # Таможенное оформление
            "duty": 0.0,
            "vat": 0.0,
            "total": 50.0
        }
        
        if tnved_info and tnved_info.duty_rate:
            # Рассчитываем пошлину
            duty_amount = float(request.weight) * float(tnved_info.duty_rate) / 100
            services["duty"] = duty_amount
            services["total"] += duty_amount
        
        if tnved_info and tnved_info.vat_rate:
            # Рассчитываем НДС
            vat_base = float(request.weight) * 2.0  # Примерная стоимость товара
            vat_amount = vat_base * float(tnved_info.vat_rate) / 100
            services["vat"] = vat_amount
            services["total"] += vat_amount
        
        return services
    
    def _calculate_additional_services(
        self,
        request: CalculationRequest,
        delivery_type: DeliveryType,
        tnved_info: Optional[TNVEDInfo]
    ) -> Dict[str, Any]:
        """Расчёт дополнительных услуг"""
        
        services = {
            "insurance": 0.0,
            "packaging": 0.0,
            "documentation": 0.0,
            "total": 0.0
        }
        
        # Страхование (1% от стоимости)
        estimated_value = float(request.weight) * 2.0  # Примерная стоимость
        services["insurance"] = estimated_value * 0.01
        
        # Упаковка
        if request.volume > 1.0:
            services["packaging"] = 30.0
        else:
            services["packaging"] = 15.0
        
        # Документооборот
        if delivery_type == DeliveryType.WHITE:
            services["documentation"] = 25.0
        else:
            services["documentation"] = 10.0
        
        services["total"] = services["insurance"] + services["packaging"] + services["documentation"]
        
        return services
    
    def _generate_recommendations(
        self,
        request: CalculationRequest,
        cargo_delivery: Dict[str, Any],
        white_delivery: Dict[str, Any],
        tnved_info: Optional[TNVEDInfo]
    ) -> List[str]:
        """Генерация рекомендаций"""
        
        recommendations = []
        
        # Сравнение стоимости
        cargo_cost = cargo_delivery["total_cost"]
        white_cost = white_delivery["total_cost"]
        
        if white_cost < cargo_cost * 1.3:  # Если белая доставка не намного дороже
            recommendations.append("Рекомендуем белую доставку для снижения рисков")
        else:
            recommendations.append("Карго доставка более выгодна по стоимости")
        
        # Рекомендации по документам
        if tnved_info and tnved_info.required_documents:
            recommendations.append(f"Необходимые документы: {', '.join(tnved_info.required_documents[:3])}")
        
        # Рекомендации по категории
        if request.category.value == "electronics":
            recommendations.append("Для электроники рекомендуется дополнительная страховка")
        elif request.category.value == "chemicals":
            recommendations.append("Для химии требуется специальная упаковка и разрешения")
        
        # Рекомендации по весу
        if request.weight > 1000:
            recommendations.append("Для крупных партий рекомендуем договориться о скидке")
        
        return recommendations
    
    def _get_default_tariffs(self, route: str) -> List:
        """Получение базовых тарифов если не найдены в Airtable"""
        
        from app.models.schemas import TariffInfo
        
        return [
            TariffInfo(
                route=route,
                service_type=DeliveryType.CARGO,
                price_per_kg=Decimal("2.50"),
                transit_time_days=10,
                valid_from=datetime.now()
            ),
            TariffInfo(
                route=route,
                service_type=DeliveryType.WHITE,
                price_per_kg=Decimal("4.50"),
                transit_time_days=20,
                valid_from=datetime.now()
            )
        ]
    
    async def _save_calculation(
        self, 
        request_id: str, 
        request: CalculationRequest, 
        result: CalculationResult
    ) -> None:
        """Сохранение расчёта в Airtable"""
        
        try:
            calculation_data = {
                "request_id": request_id,
                "weight": float(request.weight),
                "volume": float(request.volume),
                "category": request.category.value,
                "origin": request.origin,
                "destination": request.destination,
                "cargo_cost": result.cargo_delivery["total_cost"],
                "white_cost": result.white_delivery["total_cost"]
            }
            
            await self.airtable_service.save_calculation(calculation_data)
            
        except Exception as e:
            logger.error(f"Failed to save calculation: {e}")
            # Не прерываем выполнение если сохранение не удалось
    
    async def get_calculation_by_id(self, request_id: str) -> Optional[CalculationResult]:
        """Получение расчёта по ID"""
        
        try:
            calculation_data = await self.airtable_service.get_calculation_by_id(request_id)
            
            if not calculation_data:
                return None
            
            # TODO: Восстановить полный объект CalculationResult из данных
            return None
            
        except Exception as e:
            logger.error(f"Failed to get calculation by ID: {e}")
            return None
    
    async def get_user_calculation_history(
        self, 
        user_id: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получение истории расчётов пользователя"""
        
        try:
            return await self.airtable_service.get_user_calculation_history(
                user_id=user_id,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"Failed to get calculation history: {e}")
            return []
    
    async def delete_calculation(self, request_id: str) -> bool:
        """Удаление расчёта"""
        
        try:
            # TODO: Реализовать удаление из Airtable
            logger.info(f"Calculation deletion requested: {request_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete calculation: {e}")
            return False
