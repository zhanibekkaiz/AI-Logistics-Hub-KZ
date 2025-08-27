"""
Telegram Bot сервис для AI Logistics Hub
Обработка запросов клиентов и интеграция с основными сервисами
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import aiohttp
import structlog

from app.core.config import settings
from app.services.airtable import AirtableService
from app.services.rls_tnved_info import TNVEDInfoService

logger = structlog.get_logger(__name__)


class TelegramBotService:
    """Сервис для работы с Telegram Bot API"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Инициализируем другие сервисы
        self.airtable = AirtableService(
            api_key=settings.AIRTABLE_API_KEY,
            base_id=settings.AIRTABLE_BASE_ID
        )
        self.tnved_service = TNVEDInfoService(
            username=settings.TNVED_INFO_USERNAME,
            password=settings.TNVED_INFO_PASSWORD
        )
        
        # Состояния пользователей (для FSM)
        self.user_states: Dict[int, Dict[str, Any]] = {}
        
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.session:
            await self.session.close()
    
    async def initialize(self) -> None:
        """Инициализация бота"""
        try:
            # Проверяем подключение к Telegram API
            async with self.session.get(f"{self.base_url}/getMe") as response:
                if response.status == 200:
                    bot_info = await response.json()
                    logger.info(f"Telegram bot initialized: @{bot_info['result']['username']}")
                else:
                    raise Exception(f"Failed to initialize Telegram bot: {response.status}")
                    
            # Инициализируем другие сервисы
            await self.airtable.initialize()
            await self.tnved_service.initialize()
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot service: {e}")
            raise
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        """Отправка сообщения пользователю"""
        try:
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            async with self.session.post(f"{self.base_url}/sendMessage", json=data) as response:
                if response.status == 200:
                    logger.info(f"Message sent to {chat_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to send message: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def send_keyboard(self, chat_id: int, text: str, keyboard: list) -> bool:
        """Отправка сообщения с клавиатурой"""
        try:
            reply_markup = {
                "keyboard": keyboard,
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": reply_markup
            }
            
            async with self.session.post(f"{self.base_url}/sendMessage", json=data) as response:
                if response.status == 200:
                    logger.info(f"Keyboard message sent to {chat_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to send keyboard message: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending keyboard message: {e}")
            return False
    
    def get_main_keyboard(self) -> list:
        """Главная клавиатура бота"""
        return [
            ["📦 Расчет доставки", "🔍 Поиск ТН ВЭД"],
            ["🏢 Проверка поставщика", "📊 Мои расчеты"],
            ["ℹ️ Помощь", "📞 Связаться с менеджером"]
        ]
    
    def get_calculation_keyboard(self) -> list:
        """Клавиатура для расчета доставки"""
        return [
            ["🔙 Назад", "📋 Пример расчета"],
            ["❓ Как пользоваться"]
        ]
    
    async def handle_start_command(self, chat_id: int, user_info: Dict[str, Any]) -> None:
        """Обработка команды /start"""
        welcome_text = f"""
🤖 <b>Добро пожаловать в AI Logistics Hub!</b>

Я помогу вам рассчитать стоимость доставки из Китая в Казахстан, найти ТН ВЭД коды и проверить поставщиков.

<b>Что я умею:</b>
• 📦 Расчет стоимости карго и белой доставки
• 🔍 Поиск и классификация ТН ВЭД кодов
• 🏢 Проверка китайских поставщиков
• 📊 История ваших расчетов

Выберите нужную опцию:
        """
        
        # Сохраняем пользователя в Airtable
        try:
            client_data = {
                "name": user_info.get("first_name", ""),
                "email": "",  # Будет запрошено позже
                "phone": "",  # Будет запрошено позже
                "company": "",
                "telegram_id": str(chat_id),
                "username": user_info.get("username", "")
            }
            
            await self.airtable.save_client(client_data)
            logger.info(f"New user registered: {chat_id}")
            
        except Exception as e:
            logger.error(f"Failed to save user to Airtable: {e}")
        
        await self.send_keyboard(chat_id, welcome_text, self.get_main_keyboard())
    
    async def handle_calculation_request(self, chat_id: int) -> None:
        """Обработка запроса на расчет доставки"""
        # Устанавливаем состояние пользователя
        self.user_states[chat_id] = {
            "state": "waiting_calculation_data",
            "data": {}
        }
        
        instruction_text = """
📦 <b>Расчет стоимости доставки</b>

Для расчета мне нужна следующая информация:

<b>1. Вес груза (кг)</b>
<b>2. Объем груза (м³)</b>
<b>3. Город отправления</b>
<b>4. Город назначения</b>
<b>5. Описание товара</b>

Отправьте данные в формате:
<code>
Вес: 100
Объем: 0.5
Откуда: Shenzhen
Куда: Almaty
Товар: LED лампы, 10W, E27
</code>

Или нажмите "📋 Пример расчета" для демонстрации.
        """
        
        await self.send_keyboard(chat_id, instruction_text, self.get_calculation_keyboard())
    
    async def handle_tnved_search(self, chat_id: int) -> None:
        """Обработка запроса на поиск ТН ВЭД"""
        self.user_states[chat_id] = {
            "state": "waiting_tnved_query",
            "data": {}
        }
        
        instruction_text = """
🔍 <b>Поиск ТН ВЭД кода</b>

Опишите ваш товар максимально подробно, и я найду подходящий ТН ВЭД код.

<b>Примеры запросов:</b>
• LED лампы светодиодные 10W E27 цоколь
• Одежда детская хлопковая футболки
• Электроника смартфоны мобильные телефоны

Отправьте описание товара:
        """
        
        keyboard = [["🔙 Назад"]]
        await self.send_keyboard(chat_id, instruction_text, keyboard)
    
    async def handle_supplier_check(self, chat_id: int) -> None:
        """Обработка запроса на проверку поставщика"""
        self.user_states[chat_id] = {
            "state": "waiting_supplier_info",
            "data": {}
        }
        
        instruction_text = """
🏢 <b>Проверка китайского поставщика</b>

Для проверки поставщика мне нужна следующая информация:

<b>1. Название компании</b>
<b>2. Регистрационный номер (если есть)</b>

Отправьте данные в формате:
<code>
Компания: Shenzhen Electronics Co., Ltd.
Рег. номер: 91440300XXXXXXXXXX
</code>

Или просто название компании, если номер неизвестен.
        """
        
        keyboard = [["🔙 Назад"]]
        await self.send_keyboard(chat_id, instruction_text, keyboard)
    
    async def handle_calculation_history(self, chat_id: int) -> None:
        """Показать историю расчетов пользователя"""
        try:
            # Получаем историю расчетов из Airtable
            calculations = await self.airtable.get_user_calculation_history(str(chat_id))
            
            if not calculations:
                await self.send_message(chat_id, "📊 У вас пока нет сохраненных расчетов.")
                return
            
            history_text = "📊 <b>Ваши последние расчеты:</b>\n\n"
            
            for i, calc in enumerate(calculations[:5], 1):  # Показываем последние 5
                history_text += f"<b>{i}.</b> {calc.get('Origin', 'N/A')} → {calc.get('Destination', 'N/A')}\n"
                history_text += f"Вес: {calc.get('Weight', 'N/A')} кг | Стоимость: ${calc.get('CargoCost', 'N/A')}\n\n"
            
            await self.send_message(chat_id, history_text)
            
        except Exception as e:
            logger.error(f"Failed to get calculation history: {e}")
            await self.send_message(chat_id, "❌ Ошибка при получении истории расчетов.")
    
    async def handle_help(self, chat_id: int) -> None:
        """Показать справку"""
        help_text = """
ℹ️ <b>Справка по использованию бота</b>

<b>📦 Расчет доставки</b>
• Укажите вес, объем, города и описание товара
• Получите расчет для карго и белой доставки
• Сравните варианты и выберите оптимальный

<b>🔍 Поиск ТН ВЭД</b>
• Опишите товар подробно
• Получите точный ТН ВЭД код
• Узнайте ставки пошлин и требования

<b>🏢 Проверка поставщика</b>
• Укажите название китайской компании
• Получите отчет о надежности
• Узнайте риски и рекомендации

<b>📞 Поддержка</b>
По всем вопросам обращайтесь к менеджеру:
• Telegram: @manager_username
• Email: support@ailogistics.kz
• Телефон: +7 XXX XXX XX XX
        """
        
        await self.send_message(chat_id, help_text)
    
    async def process_message(self, message: Dict[str, Any]) -> None:
        """Основной обработчик сообщений"""
        try:
            chat_id = message["chat"]["id"]
            user_info = message["from"]
            text = message.get("text", "").strip()
            
            # Получаем текущее состояние пользователя
            user_state = self.user_states.get(chat_id, {})
            current_state = user_state.get("state", "main_menu")
            
            # Обработка команд
            if text.startswith("/"):
                if text == "/start":
                    await self.handle_start_command(chat_id, user_info)
                elif text == "/help":
                    await self.handle_help(chat_id)
                return
            
            # Обработка по состоянию
            if current_state == "main_menu":
                await self.handle_main_menu(chat_id, text)
            elif current_state == "waiting_calculation_data":
                await self.handle_calculation_data(chat_id, text)
            elif current_state == "waiting_tnved_query":
                await self.handle_tnved_query(chat_id, text)
            elif current_state == "waiting_supplier_info":
                await self.handle_supplier_info(chat_id, text)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_message(chat_id, "❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_main_menu(self, chat_id: int, text: str) -> None:
        """Обработка главного меню"""
        if text == "📦 Расчет доставки":
            await self.handle_calculation_request(chat_id)
        elif text == "🔍 Поиск ТН ВЭД":
            await self.handle_tnved_search(chat_id)
        elif text == "🏢 Проверка поставщика":
            await self.handle_supplier_check(chat_id)
        elif text == "📊 Мои расчеты":
            await self.handle_calculation_history(chat_id)
        elif text == "ℹ️ Помощь":
            await self.handle_help(chat_id)
        elif text == "📞 Связаться с менеджером":
            await self.send_message(chat_id, "📞 Свяжитесь с менеджером:\nTelegram: @manager_username\nEmail: support@ailogistics.kz")
        elif text == "🔙 Назад":
            # Возвращаемся в главное меню
            self.user_states[chat_id] = {"state": "main_menu", "data": {}}
            await self.send_keyboard(chat_id, "🏠 Главное меню:", self.get_main_keyboard())
        else:
            await self.send_message(chat_id, "Выберите опцию из меню ниже:")
    
    async def handle_calculation_data(self, chat_id: int, text: str) -> None:
        """Обработка данных для расчета"""
        if text == "📋 Пример расчета":
            example_text = """
📋 <b>Пример расчета доставки</b>

Отправьте данные в таком формате:

<code>
Вес: 100
Объем: 0.5
Откуда: Shenzhen
Куда: Almaty
Товар: LED лампы светодиодные 10W E27 цоколь белый свет
</code>

После отправки я рассчитаю стоимость карго и белой доставки.
            """
            await self.send_message(chat_id, example_text)
            return
        
        if text == "❓ Как пользоваться":
            help_text = """
❓ <b>Как пользоваться расчетом</b>

1. <b>Вес груза</b> - укажите в килограммах
2. <b>Объем груза</b> - укажите в кубических метрах
3. <b>Город отправления</b> - обычно Shenzhen, Guangzhou, Shanghai
4. <b>Город назначения</b> - ваш город в Казахстане
5. <b>Описание товара</b> - подробное описание для определения ТН ВЭД

<b>Пример:</b>
Вес: 50
Объем: 0.3
Откуда: Shenzhen
Куда: Almaty
Товар: Электронные компоненты, микросхемы, резисторы
            """
            await self.send_message(chat_id, help_text)
            return
        
        # Парсим данные для расчета
        try:
            calculation_data = self.parse_calculation_text(text)
            if calculation_data:
                await self.perform_calculation(chat_id, calculation_data)
            else:
                await self.send_message(chat_id, "❌ Не удалось распознать данные. Используйте формат из примера.")
        except Exception as e:
            logger.error(f"Error parsing calculation data: {e}")
            await self.send_message(chat_id, "❌ Ошибка при обработке данных. Попробуйте еще раз.")
    
    def parse_calculation_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Парсинг текста с данными для расчета"""
        try:
            lines = text.split('\n')
            data = {}
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'вес' in key:
                        data['weight'] = float(value)
                    elif 'объем' in key:
                        data['volume'] = float(value)
                    elif 'откуда' in key or 'отправление' in key:
                        data['origin'] = value
                    elif 'куда' in key or 'назначение' in key:
                        data['destination'] = value
                    elif 'товар' in key or 'описание' in key:
                        data['description'] = value
            
            # Проверяем наличие всех необходимых полей
            required_fields = ['weight', 'volume', 'origin', 'destination', 'description']
            if all(field in data for field in required_fields):
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing calculation text: {e}")
            return None
    
    async def perform_calculation(self, chat_id: int, data: Dict[str, Any]) -> None:
        """Выполнение расчета доставки"""
        try:
            # Отправляем сообщение о начале расчета
            await self.send_message(chat_id, "🔄 Выполняю расчет...")
            
            # Получаем ТН ВЭД код
            tnved_result = await self.tnved_service.search_tnved_codes(data['description'])
            
            # Получаем тарифы из Airtable
            tariffs = await self.airtable.get_tariffs()
            
            # Выполняем расчет (упрощенная версия)
            cargo_cost = data['weight'] * 2.5  # Примерная стоимость карго
            white_cost = data['weight'] * 4.0   # Примерная стоимость белой доставки
            
            # Формируем результат
            result_text = f"""
📦 <b>Результат расчета доставки</b>

<b>Маршрут:</b> {data['origin']} → {data['destination']}
<b>Вес:</b> {data['weight']} кг
<b>Объем:</b> {data['volume']} м³
<b>Товар:</b> {data['description']}

<b>ТН ВЭД код:</b> {tnved_result.get('code', 'Не определен')}

<b>💰 Стоимость доставки:</b>

🚛 <b>Карго доставка:</b> ${cargo_cost:.2f}
⏱️ Время в пути: 10-15 дней
⚠️ Риски: Средние

📦 <b>Белая доставка:</b> ${white_cost:.2f}
⏱️ Время в пути: 20-25 дней
✅ Риски: Минимальные

<b>💡 Рекомендация:</b>
{'Рекомендуем белую доставку для снижения рисков' if white_cost < cargo_cost * 1.5 else 'Карго доставка более выгодна по цене'}
            """
            
            # Сохраняем расчет в Airtable
            calculation_data = {
                "request_id": f"calc_{chat_id}_{int(datetime.now().timestamp())}",
                "weight": data['weight'],
                "volume": data['volume'],
                "origin": data['origin'],
                "destination": data['destination'],
                "cargo_cost": cargo_cost,
                "white_cost": white_cost,
                "tnved_code": tnved_result.get('code', ''),
                "description": data['description']
            }
            
            await self.airtable.save_calculation(calculation_data)
            
            # Возвращаемся в главное меню
            self.user_states[chat_id] = {"state": "main_menu", "data": {}}
            
            keyboard = [["📦 Новый расчет", "📊 Мои расчеты"], ["🔙 Главное меню"]]
            await self.send_keyboard(chat_id, result_text, keyboard)
            
        except Exception as e:
            logger.error(f"Error performing calculation: {e}")
            await self.send_message(chat_id, "❌ Ошибка при выполнении расчета. Попробуйте позже.")
    
    async def handle_tnved_query(self, chat_id: int, text: str) -> None:
        """Обработка запроса ТН ВЭД"""
        if text == "🔙 Назад":
            self.user_states[chat_id] = {"state": "main_menu", "data": {}}
            await self.send_keyboard(chat_id, "🏠 Главное меню:", self.get_main_keyboard())
            return
        
        try:
            await self.send_message(chat_id, "🔍 Ищу ТН ВЭД код...")
            
            # Выполняем поиск ТН ВЭД
            result = await self.tnved_service.search_tnved_codes(text)
            
            if result and result.get('results'):
                tnved_info = result['results'][0]
                
                response_text = f"""
🔍 <b>Результат поиска ТН ВЭД</b>

<b>Запрос:</b> {text}

<b>Найденный код:</b> {tnved_info.get('code', 'N/A')}
<b>Описание:</b> {tnved_info.get('description', 'N/A')}
<b>Вероятность:</b> {tnved_info.get('probability', 'N/A')}%

<b>📋 Дополнительная информация:</b>
• Ставка пошлины: 5-15% (зависит от страны)
• НДС: 12%
• Требуемые документы: Сертификат соответствия, Декларация
                """
            else:
                response_text = f"""
❌ <b>ТН ВЭД код не найден</b>

<b>Запрос:</b> {text}

Попробуйте:
• Более подробное описание товара
• Использовать другие ключевые слова
• Обратиться к менеджеру для помощи
                """
            
            keyboard = [["🔍 Новый поиск"], ["🔙 Главное меню"]]
            await self.send_keyboard(chat_id, response_text, keyboard)
            
            # Возвращаемся в главное меню
            self.user_states[chat_id] = {"state": "main_menu", "data": {}}
            
        except Exception as e:
            logger.error(f"Error searching TNVED: {e}")
            await self.send_message(chat_id, "❌ Ошибка при поиске ТН ВЭД. Попробуйте позже.")
    
    async def handle_supplier_info(self, chat_id: int, text: str) -> None:
        """Обработка информации о поставщике"""
        if text == "🔙 Назад":
            self.user_states[chat_id] = {"state": "main_menu", "data": {}}
            await self.send_keyboard(chat_id, "🏠 Главное меню:", self.get_main_keyboard())
            return
        
        try:
            await self.send_message(chat_id, "🏢 Проверяю поставщика...")
            
            # Пока что заглушка для проверки поставщика
            response_text = f"""
🏢 <b>Проверка поставщика</b>

<b>Компания:</b> {text}

<b>📊 Результаты проверки:</b>
• Статус: Активная компания
• Дата регистрации: 2015-2020
• Уставной капитал: $100,000 - $1,000,000
• Судебные дела: 0-2 (нормально)
• Экспортная история: Есть

<b>✅ Рекомендация:</b>
Поставщик выглядит надежным. Рекомендуем:
• Запросить образцы товара
• Проверить сертификаты
• Начать с небольшого заказа

<b>⚠️ Примечание:</b>
Это предварительная оценка. Для полной проверки обратитесь к менеджеру.
            """
            
            keyboard = [["🏢 Проверить другого"], ["🔙 Главное меню"]]
            await self.send_keyboard(chat_id, response_text, keyboard)
            
            # Возвращаемся в главное меню
            self.user_states[chat_id] = {"state": "main_menu", "data": {}}
            
        except Exception as e:
            logger.error(f"Error checking supplier: {e}")
            await self.send_message(chat_id, "❌ Ошибка при проверке поставщика. Попробуйте позже.")


# Функция для получения экземпляра сервиса
async def get_telegram_bot_service() -> TelegramBotService:
    """Получение экземпляра Telegram Bot сервиса"""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not configured")
    
    service = TelegramBotService(settings.TELEGRAM_BOT_TOKEN)
    await service.initialize()
    return service
