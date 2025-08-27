#!/usr/bin/env python3
"""
Скрипт для заполнения тарифов в Airtable
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import json

# Загружаем переменные окружения
load_dotenv()

async def fill_tariffs():
    """Заполнение тарифов в Airtable"""
    
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    if not api_key or not base_id:
        print("❌ Отсутствуют API ключи в .env файле")
        return
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Тарифы для заполнения
    tariffs_data = [
        # Карго доставка
        {
            "fields": {
                "Route": "Shenzhen-Almaty",
                "ServiceType": "cargo",
                "PricePerKg": 2.5,
                "TransitTime": 12,
                "Notes": "Карго доставка, контейнер"
            }
        },
        {
            "fields": {
                "Route": "Guangzhou-Almaty",
                "ServiceType": "cargo",
                "PricePerKg": 2.3,
                "TransitTime": 14,
                "Notes": "Карго доставка, контейнер"
            }
        },
        {
            "fields": {
                "Route": "Shanghai-Almaty",
                "ServiceType": "cargo",
                "PricePerKg": 2.8,
                "TransitTime": 15,
                "Notes": "Карго доставка, контейнер"
            }
        },
        {
            "fields": {
                "Route": "Shenzhen-Astana",
                "ServiceType": "cargo",
                "PricePerKg": 2.7,
                "TransitTime": 13,
                "Notes": "Карго доставка, контейнер"
            }
        },
        {
            "fields": {
                "Route": "Guangzhou-Astana",
                "ServiceType": "cargo",
                "PricePerKg": 2.5,
                "TransitTime": 15,
                "Notes": "Карго доставка, контейнер"
            }
        },
        
        # Белая доставка
        {
            "fields": {
                "Route": "Shenzhen-Almaty",
                "ServiceType": "white",
                "PricePerKg": 4.2,
                "TransitTime": 18,
                "Notes": "Белая доставка, полное оформление"
            }
        },
        {
            "fields": {
                "Route": "Guangzhou-Almaty",
                "ServiceType": "white",
                "PricePerKg": 4.0,
                "TransitTime": 20,
                "Notes": "Белая доставка, полное оформление"
            }
        },
        {
            "fields": {
                "Route": "Shanghai-Almaty",
                "ServiceType": "white",
                "PricePerKg": 4.5,
                "TransitTime": 22,
                "Notes": "Белая доставка, полное оформление"
            }
        },
        {
            "fields": {
                "Route": "Shenzhen-Astana",
                "ServiceType": "white",
                "PricePerKg": 4.3,
                "TransitTime": 19,
                "Notes": "Белая доставка, полное оформление"
            }
        },
        {
            "fields": {
                "Route": "Guangzhou-Astana",
                "ServiceType": "white",
                "PricePerKg": 4.1,
                "TransitTime": 21,
                "Notes": "Белая доставка, полное оформление"
            }
        },
        
        # Дополнительные маршруты
        {
            "fields": {
                "Route": "Shenzhen-Shymkent",
                "ServiceType": "cargo",
                "PricePerKg": 2.6,
                "TransitTime": 14,
                "Notes": "Карго доставка, контейнер"
            }
        },
        {
            "fields": {
                "Route": "Shenzhen-Shymkent",
                "ServiceType": "white",
                "PricePerKg": 4.4,
                "TransitTime": 20,
                "Notes": "Белая доставка, полное оформление"
            }
        },
        {
            "fields": {
                "Route": "Guangzhou-Aktobe",
                "ServiceType": "cargo",
                "PricePerKg": 2.9,
                "TransitTime": 16,
                "Notes": "Карго доставка, контейнер"
            }
        },
        {
            "fields": {
                "Route": "Guangzhou-Aktobe",
                "ServiceType": "white",
                "PricePerKg": 4.7,
                "TransitTime": 23,
                "Notes": "Белая доставка, полное оформление"
            }
        }
    ]
    
    print("🚀 Заполнение тарифов в Airtable")
    print("=" * 50)
    
    url = f"https://api.airtable.com/v0/{base_id}/Tariffs"
    
    created_count = 0
    
    for i, tariff in enumerate(tariffs_data, 1):
        try:
            print(f"📝 Создаю тариф {i}/{len(tariffs_data)}: {tariff['fields']['Route']} - {tariff['fields']['ServiceType']}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=tariff) as response:
                    if response.status == 200:
                        result = await response.json()
                        record_id = result["id"]
                        print(f"✅ Создан тариф (ID: {record_id})")
                        created_count += 1
                    else:
                        error_text = await response.text()
                        print(f"❌ Ошибка создания тарифа: {error_text}")
                        
        except Exception as e:
            print(f"❌ Ошибка создания тарифа: {e}")
    
    print("\n" + "=" * 50)
    print(f"✅ Заполнение завершено! Создано тарифов: {created_count}/{len(tariffs_data)}")

if __name__ == "__main__":
    asyncio.run(fill_tariffs())
