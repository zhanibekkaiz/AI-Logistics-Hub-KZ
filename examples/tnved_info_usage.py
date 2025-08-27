#!/usr/bin/env python3
"""
Пример использования API tnved.info в AI Logistics Hub
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any


class TNVEDInfoClient:
    """Клиент для работы с API tnved.info"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1/tnved-info"
    
    async def search_tnved_codes(self, query: str, group: str = None) -> Dict[str, Any]:
        """Поиск ТН ВЭД кодов"""
        
        url = f"{self.api_base}/search"
        params = {"query": query}
        if group:
            params["group"] = group
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                return await response.json()
    
    async def get_tnved_info(self, code: str) -> Dict[str, Any]:
        """Получение информации о коде ТН ВЭД"""
        
        url = f"{self.api_base}/code/{code}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
    
    async def classify_product(self, description: str, category: str = None) -> Dict[str, Any]:
        """Классификация товара"""
        
        url = f"{self.api_base}/classify"
        data = {"description": description}
        if category:
            data["category"] = category
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                return await response.json()
    
    async def get_license_info(self) -> Dict[str, Any]:
        """Получение информации о лицензии"""
        
        url = f"{self.api_base}/license"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья API"""
        
        url = f"{self.api_base}/health"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()


async def main():
    """Основная функция с примерами использования"""
    
    print("🚀 Пример использования API tnved.info")
    print("=" * 50)
    
    # Создаём клиент
    client = TNVEDInfoClient()
    
    try:
        # 1. Проверка здоровья API
        print("\n1️⃣ Проверка здоровья API...")
        health = await client.health_check()
        print(f"Статус: {health.get('message', 'Unknown')}")
        
        # 2. Информация о лицензии
        print("\n2️⃣ Информация о лицензии...")
        try:
            license_info = await client.get_license_info()
            print(f"Рабочее место: {license_info.get('work_place', 'N/A')}")
            print(f"Осталось запросов: {license_info.get('remain', 0)}")
        except Exception as e:
            print(f"Ошибка получения лицензии: {e}")
        
        # 3. Поиск по описанию товара
        print("\n3️⃣ Поиск по описанию товара...")
        search_result = await client.search_tnved_codes("LED light bulbs")
        
        if search_result.get("success"):
            results = search_result.get("results", [])
            print(f"Найдено результатов: {len(results)}")
            
            if results:
                best_result = results[0]
                print(f"Лучший результат:")
                print(f"  Код: {best_result.get('code', 'N/A')}")
                print(f"  Описание: {best_result.get('description', 'N/A')}")
                print(f"  Вероятность: {best_result.get('probability', 0):.2f}%")
        else:
            print(f"Ошибка поиска: {search_result.get('error_message', 'Unknown error')}")
        
        # 4. Получение информации о конкретном коде
        print("\n4️⃣ Информация о коде ТН ВЭД...")
        try:
            tnved_info = await client.get_tnved_info("8539310000")
            print(f"Код: {tnved_info.get('code', 'N/A')}")
            print(f"Описание: {tnved_info.get('description', 'N/A')}")
            print(f"Пошлина: {tnved_info.get('duty_rate', 'N/A')}%")
            print(f"НДС: {tnved_info.get('vat_rate', 'N/A')}%")
            print(f"Документы: {', '.join(tnved_info.get('required_documents', []))}")
        except Exception as e:
            print(f"Ошибка получения информации: {e}")
        
        # 5. Классификация товара
        print("\n5️⃣ Классификация товара...")
        classification = await client.classify_product(
            description="LED light bulbs, 10W, E27 base, white color, energy efficient",
            category="electronics"
        )
        
        if "code" in classification:
            print(f"Определён код: {classification.get('code', 'N/A')}")
            print(f"Описание: {classification.get('description', 'N/A')}")
            print(f"Документы: {', '.join(classification.get('required_documents', []))}")
        else:
            print(f"Ошибка классификации: {classification.get('detail', 'Unknown error')}")
        
        # 6. Дополнительные примеры поиска
        print("\n6️⃣ Дополнительные примеры поиска...")
        
        examples = [
            ("МАЙКИ ТРИКОТАЖНЫЕ", None),
            ("3921906000", None),  # Код из документации
            ("ЛАМПЫ СВЕТОДИОДНЫЕ", "8539"),
            ("ЧАЙ ЗЕЛЕНЫЙ", "0901"),
            ("КРАСКИ И ЛАКИ", "3208")
        ]
        
        for query, group in examples:
            print(f"\nПоиск: '{query}'" + (f" (группа: {group})" if group else ""))
            try:
                result = await client.search_tnved_codes(query, group)
                if result.get("success"):
                    results = result.get("results", [])
                    if results:
                        best = results[0]
                        print(f"  ✅ {best.get('code', 'N/A')} - {best.get('description', 'N/A')[:50]}...")
                    else:
                        print("  ❌ Результаты не найдены")
                else:
                    print(f"  ❌ Ошибка: {result.get('error_message', 'Unknown error')}")
            except Exception as e:
                print(f"  ❌ Исключение: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Примеры использования завершены!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("Убедитесь, что сервер запущен на http://localhost:8000")


if __name__ == "__main__":
    print("🚀 Запуск примеров использования API tnved.info")
    print("Убедитесь, что сервер запущен: uvicorn app.main:app --reload")
    print()
    
    asyncio.run(main())
