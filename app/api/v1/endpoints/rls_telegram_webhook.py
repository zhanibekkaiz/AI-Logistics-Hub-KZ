"""
Telegram Bot Webhook endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

from app.services.rls_telegram_bot import TelegramBotService, get_telegram_bot_service

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    bot_service: TelegramBotService = Depends(get_telegram_bot_service)
):
    """Вебхук для получения сообщений от Telegram"""
    try:
        update_data = await request.json()
        logger.info(f"Received Telegram update: {update_data}")
        
        if "message" in update_data:
            await bot_service.process_message(update_data["message"])
        
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/bot/info")
async def get_bot_info(
    bot_service: TelegramBotService = Depends(get_telegram_bot_service)
):
    """Получение информации о боте"""
    try:
        async with bot_service.session.get(f"{bot_service.base_url}/getMe") as response:
            if response.status == 200:
                bot_info = await response.json()
                return bot_info
            else:
                raise HTTPException(status_code=500, detail="Failed to get bot info")
                
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
