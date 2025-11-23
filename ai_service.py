"""
Модуль для работы с Gemini AI для классификации товаров по кодам ТН ВЭД.

ВАЖНО: Этот модуль использует ТОЛЬКО Gemini AI (Google).
OpenAI API отключен - не используется и не импортируется.
"""

import json
import re
import logging
import asyncio
from typing import List, Dict, Optional
import google.generativeai as genai

# ВАЖНО: OpenAI не используется в этом модуле
# Используется только google.generativeai (Gemini)

logger = logging.getLogger(__name__)

# Константы для конфигурации
MAX_DESCRIPTION_LENGTH = 1000
GEMINI_TIMEOUT = 30  # секунд
MAX_RETRIES = 3
RETRY_DELAY = 1  # секунд


def _validate_product_description(description: str) -> bool:
    """
    Валидация описания товара.
    
    Args:
        description: Описание товара для валидации
        
    Returns:
        True если валидно, False иначе
    """
    if not description or not description.strip():
        return False
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return False
    # Проверка на потенциально опасные паттерны
    dangerous_patterns = ['<script', 'javascript:', 'onerror=']
    description_lower = description.lower()
    for pattern in dangerous_patterns:
        if pattern in description_lower:
            logger.warning(f"Обнаружен потенциально опасный паттерн: {pattern}")
            return False
    return True


async def suggest_hs_codes(product_description: str, gemini_api_key: str) -> List[Dict[str, str]]:
    """
    Предложить коды ТН ВЭД на основе описания товара от пользователя.
    
    Args:
        product_description: Описание товара от пользователя
        gemini_api_key: API ключ для Gemini
        
    Returns:
        Список словарей с кодами и причинами, например:
        [{"code": "8517130000", "reason": "Смартфоны"}, ...]
    """
    # Валидация входных данных
    if not _validate_product_description(product_description):
        logger.error(f"Некорректное описание товара: длина={len(product_description) if product_description else 0}")
        return []
    
    if not gemini_api_key or not gemini_api_key.strip():
        logger.error("GEMINI_API_KEY не установлен")
        return []
    
    # Выполняем запрос с retry логикой
    for attempt in range(MAX_RETRIES):
        try:
            # Настройка Gemini API
            genai.configure(api_key=gemini_api_key)
            
            # Выбор модели
            model = genai.GenerativeModel('gemini-pro')
            
            # Системный промпт
            system_prompt = """Ты — профессиональный таможенный брокер ЕАЭС. Твоя задача — классифицировать товар.

1. Проанализируй описание пользователя.
2. Подбери 3 наиболее вероятных кода ТН ВЭД (10 знаков).
3. Для каждого кода дай краткое пояснение (1 предложение), почему он подходит.
4. ВЕРНИ ОТВЕТ ТОЛЬКО В ФОРМАТЕ JSON следующего вида, без лишнего текста и markdown разметки:

[
  {"code": "8517130000", "reason": "Смартфоны"},
  {"code": "8517120000", "reason": "Телефоны для сотовых сетей (устаревший, но возможный)"},
  ...
]

ВАЖНО: Отвечай ТОЛЬКО JSON массивом, без дополнительного текста, без markdown разметки, без символов ```json или ```."""
            
            # Полный промпт
            full_prompt = f"{system_prompt}\n\nОписание товара: {product_description}"
            
            logger.info(f"Отправка запроса в Gemini для товара (попытка {attempt + 1}/{MAX_RETRIES}): {product_description[:50]}...")
            
            # Отправка запроса с таймаутом
            # Примечание: google.generativeai не поддерживает async напрямую,
            # поэтому используем executor для неблокирующего выполнения
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: model.generate_content(full_prompt)),
                timeout=GEMINI_TIMEOUT
            )
        
            # Получение текста ответа
            if not response or not hasattr(response, 'text') or not response.text:
                raise ValueError("Пустой ответ от Gemini API")
            
            response_text = response.text.strip()
            
            logger.debug(f"Ответ от Gemini (сырой): {response_text[:200]}...")
            
            # Очистка от markdown разметки (```json ... ```)
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            response_text = response_text.strip()
            
            # Попытка найти JSON в ответе (на случай, если модель добавила лишний текст)
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            # Парсинг JSON
            codes_list = json.loads(response_text)
            
            # Валидация структуры
            if not isinstance(codes_list, list):
                logger.error("Ответ от Gemini не является списком")
                return []
            
            # Проверка формата каждого элемента
            validated_list = []
            for item in codes_list:
                if isinstance(item, dict) and "code" in item and "reason" in item:
                    # Убеждаемся, что код имеет правильный формат (10 цифр)
                    code = str(item["code"]).strip()
                    if code.isdigit() and len(code) == 10:
                        validated_list.append({
                            "code": code,
                            "reason": str(item["reason"])[:200]  # Ограничение длины причины
                        })
                    else:
                        logger.warning(f"Некорректный формат кода: {code}")
                else:
                    logger.warning(f"Некорректный формат элемента: {item}")
            
            logger.info(f"Получено {len(validated_list)} валидных кодов ТН ВЭД")
            return validated_list
            
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут при запросе к Gemini API (попытка {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                continue
            else:
                logger.error("Исчерпаны все попытки запроса к Gemini API")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от Gemini: {e}")
            logger.error(f"Текст ответа: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
                continue
            else:
                return []
                
        except Exception as e:
            logger.error(f"Ошибка при работе с Gemini API (попытка {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
                continue
            else:
                return []
    
    # Если дошли сюда, значит все попытки исчерпаны
    return []

