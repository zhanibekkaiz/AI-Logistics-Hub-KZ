#!/usr/bin/env python3
"""
Скрипт для получения структуры таблиц Airtable
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import json

# Загружаем переменные окружения
load_dotenv()

async def get_table_structure():
    """Получение структуры таблиц Airtable"""
    
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    if not api_key or not base_id:
        print("❌ Отсутствуют API ключи в .env файле")
        return
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Тестируем только одну таблицу для начала
    table = "Orders"
    
    print(f"\n📊 Структура таблицы: {table}")
    print("=" * 50)
    
    url = f"https://api.airtable.com/v0/{base_id}/{table}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print("📋 Полный JSON ответ:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Ошибка: {error_text}")
                    
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

if __name__ == "__main__":
    asyncio.run(get_table_structure())
