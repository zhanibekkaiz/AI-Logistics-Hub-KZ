"""
Основной файл Telegram-бота "AI Таможенный Брокер".
Использует AI для классификации товаров и API ЕЭК для получения официальной информации.

ВАЖНО: Этот бот использует ТОЛЬКО Gemini AI (Google).
OpenAI API отключен для этого бота, чтобы избежать конфликтов.
"""

import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from eaeu_api import EaeuClient
from ai_service import suggest_hs_codes

# Загрузка переменных окружения
load_dotenv()

# ВАЖНО: OpenAI API отключен для этого бота
# Этот бот использует только Gemini AI (GEMINI_API_KEY)
# Переменная OPENAI_API_KEY не используется и игнорируется

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получение токенов из переменных окружения
# Поддержка обоих вариантов для совместимости
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not TELEGRAM_TOKEN:
    raise ValueError(
        "TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN не установлен в переменных окружения. "
        "Создайте бота через @BotFather и добавьте токен в .env файл."
    )
if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY не установлен в переменных окружения. "
        "Получите ключ на https://makersuite.google.com/app/apikey и добавьте в .env файл."
    )

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Глобальный экземпляр клиента ЕЭК
eaeu_client = EaeuClient()


class ProductStates(StatesGroup):
    """Состояния FSM для бота."""
    waiting_for_description = State()


def create_codes_keyboard(codes_list: list) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру с кнопками для выбора кодов ТН ВЭД.
    
    Args:
        codes_list: Список словарей с ключами "code" и "reason"
        
    Returns:
        InlineKeyboardMarkup с кнопками
    """
    buttons = []
    for item in codes_list:
        code = item["code"]
        reason = item["reason"]
        # Ограничиваем длину текста кнопки (Telegram ограничение)
        button_text = f"{code} - {reason[:30]}..." if len(reason) > 30 else f"{code} - {reason}"
        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"check_{code}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.set_state(ProductStates.waiting_for_description)
    await message.answer(
        "👋 Привет! Я AI Таможенный Брокер.\n\n"
        "Я помогу вам найти код ТН ВЭД для вашего товара.\n\n"
        "📝 Просто опишите товар, и я предложу наиболее подходящие коды.\n\n"
        "Например: 'Женские кроссовки из кожзама'"
    )


@dp.message(ProductStates.waiting_for_description)
async def process_product_description(message: Message, state: FSMContext):
    """Обработка описания товара от пользователя."""
    product_description = message.text.strip() if message.text else ""
    
    # Валидация входных данных
    if not product_description:
        await message.answer("Пожалуйста, опишите товар.")
        return
    
    if len(product_description) > 1000:
        await message.answer(
            "❌ Описание товара слишком длинное (максимум 1000 символов).\n\n"
            "Пожалуйста, сократите описание."
        )
        return
    
    # Отправляем сообщение о том, что ищем коды
    status_message = await message.answer("🔍 Ищу коды ТН ВЭД...")
    
    try:
        # Получаем предложения от AI (async)
        codes_list = await suggest_hs_codes(product_description, GEMINI_API_KEY)
        
        if not codes_list:
            await status_message.edit_text(
                "❌ К сожалению, не удалось найти подходящие коды ТН ВЭД.\n\n"
                "Попробуйте описать товар более подробно или используйте другие формулировки."
            )
            return
        
        # Создаем клавиатуру с кнопками
        keyboard = create_codes_keyboard(codes_list)
        
        # Формируем текст сообщения
        codes_text = "\n".join([
            f"• {item['code']} - {item['reason']}"
            for item in codes_list
        ])
        
        await status_message.edit_text(
            f"✅ Найдено {len(codes_list)} вариантов:\n\n{codes_text}\n\n"
            "Выберите наиболее подходящий вариант:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке описания товара: {e}")
        await status_message.edit_text(
            "❌ Произошла ошибка при поиске кодов. Попробуйте позже."
        )


@dp.callback_query(F.data.startswith("check_"))
async def process_code_check(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия на кнопку с кодом ТН ВЭД."""
    # Извлекаем код из callback_data
    code = callback.data.replace("check_", "")
    
    # Валидация кода ТН ВЭД
    if not code or not code.isdigit() or len(code) != 10:
        await callback.answer("❌ Некорректный формат кода ТН ВЭД", show_alert=True)
        logger.warning(f"Некорректный код ТН ВЭД от пользователя: {code}")
        return
    
    await callback.answer("⏳ Получаю информацию из базы ЕЭК...")
    
    try:
        # Получаем официальную информацию из API ЕЭК
        tnved_info = await eaeu_client.get_tnved_info(code)
        
        if not tnved_info:
            await callback.message.answer(
                f"❌ Код {code} не найден в базе ЕЭК.\n\n"
                "Возможно, код некорректен или база данных временно недоступна."
            )
            return
        
        official_description = tnved_info.get("name", "Описание не найдено")
        
        # Формируем итоговое сообщение
        response_text = (
            f"✅ Выбран код: {code}\n\n"
            f"📄 Официальное описание ЕЭК:\n{official_description}\n\n"
            f"💡 Совет: Проверьте соответствие описания вашему товару. "
            f"При необходимости обратитесь к таможенному брокеру для уточнения."
        )
        
        await callback.message.answer(response_text)
        
        # Сбрасываем состояние
        await state.set_state(ProductStates.waiting_for_description)
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о коде {code}: {e}")
        await callback.message.answer(
            f"❌ Произошла ошибка при получении информации о коде {code}.\n\n"
            "Попробуйте позже или обратитесь к таможенному брокеру."
        )


@dp.message()
async def handle_other_messages(message: Message, state: FSMContext):
    """Обработка прочих сообщений."""
    current_state = await state.get_state()
    if current_state != ProductStates.waiting_for_description:
        await state.set_state(ProductStates.waiting_for_description)
    
    await message.answer(
        "📝 Пожалуйста, опишите товар, для которого нужно найти код ТН ВЭД.\n\n"
        "Или используйте команду /start для начала работы."
    )


async def on_startup():
    """Действия при запуске бота."""
    logger.info("Бот запущен")
    # Инициализируем клиент ЕЭК (находим ID справочника)
    await eaeu_client._ensure_tnved_dictionary_id()
    logger.info("Клиент ЕЭК инициализирован")


async def on_shutdown():
    """Действия при остановке бота."""
    logger.info("Бот останавливается")
    await eaeu_client.close()
    await bot.session.close()


async def main():
    """Основная функция запуска бота."""
    try:
        # Регистрация обработчиков событий
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Запуск polling
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")

