"""
Telegram Bot Webhook endpoints
"""

import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.services.rls_telegram_bot import TelegramBotService
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Webhook endpoint для Telegram Bot API"""
    try:
        # Получаем данные от Telegram
        body = await request.json()
        logger.info(f"Received webhook: {body}")
        
        # Проверяем, что это сообщение
        if "message" not in body:
            return JSONResponse(content={"status": "ok"})
        
        message = body["message"]
        
        # Проверяем наличие текста
        if "text" not in message:
            return JSONResponse(content={"status": "ok"})
        
        # Инициализируем бота
        async with TelegramBotService(settings.TELEGRAM_BOT_TOKEN) as bot:
            await bot.initialize()
            
            # Обрабатываем сообщение
            await bot.process_message(message)
        
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook")
async def set_webhook():
    """Установка webhook для Telegram бота"""
    try:
        import aiohttp
        
        # URL для webhook (замените на ваш домен)
        webhook_url = "https://your-domain.com/api/v1/telegram/webhook"
        
        # Устанавливаем webhook
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
        data = {"url": webhook_url}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                result = await response.json()
                
                if result.get("ok"):
                    logger.info(f"Webhook set successfully: {webhook_url}")
                    return {"status": "success", "webhook_url": webhook_url}
                else:
                    logger.error(f"Failed to set webhook: {result}")
                    return {"status": "error", "description": result.get("description")}
                    
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhook")
async def delete_webhook():
    """Удаление webhook для Telegram бота"""
    try:
        import aiohttp
        
        # Удаляем webhook
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/deleteWebhook"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                result = await response.json()
                
                if result.get("ok"):
                    logger.info("Webhook deleted successfully")
                    return {"status": "success", "message": "Webhook deleted"}
                else:
                    logger.error(f"Failed to delete webhook: {result}")
                    return {"status": "error", "description": result.get("description")}
                    
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_bot_info():
    """Получение информации о боте"""
    try:
        import aiohttp
        
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.json()
                
                if result.get("ok"):
                    bot_info = result["result"]
                    return {
                        "status": "success",
                        "bot_info": {
                            "id": bot_info.get("id"),
                            "first_name": bot_info.get("first_name"),
                            "username": bot_info.get("username"),
                            "can_join_groups": bot_info.get("can_join_groups"),
                            "can_read_all_group_messages": bot_info.get("can_read_all_group_messages"),
                            "supports_inline_queries": bot_info.get("supports_inline_queries")
                        }
                    }
                else:
                    return {"status": "error", "description": result.get("description")}
                    
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-message")
async def send_message(chat_id: int, text: str):
    """Отправка сообщения через бота"""
    try:
        async with TelegramBotService(settings.TELEGRAM_BOT_TOKEN) as bot:
            await bot.initialize()
            
            success = await bot.send_message(chat_id, text)
            
            if success:
                return {"status": "success", "message": "Message sent"}
            else:
                return {"status": "error", "message": "Failed to send message"}
                
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
