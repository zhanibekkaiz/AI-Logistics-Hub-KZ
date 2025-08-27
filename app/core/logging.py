"""
Настройка логирования для AI Logistics Hub
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    enable_console: bool = True,
    enable_file: bool = False,
    log_file: str = "logs/app.log"
) -> None:
    """
    Настройка структурированного логирования
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Формат логов (json, console)
        enable_console: Включить вывод в консоль
        enable_file: Включить запись в файл
        log_file: Путь к файлу логов
    """
    
    # Настройка стандартного логирования
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Настройка structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Настройка файлового логирования (если включено)
    if enable_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Добавляем обработчик к корневому логгеру
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Получение логгера с заданным именем
    
    Args:
        name: Имя логгера (обычно __name__)
        
    Returns:
        Настроенный логгер
    """
    return structlog.get_logger(name)


def log_request(
    logger: structlog.BoundLogger,
    method: str,
    url: str,
    status_code: int,
    duration: float,
    user_agent: str = None,
    client_ip: str = None,
    **kwargs: Any
) -> None:
    """
    Логирование HTTP запроса
    
    Args:
        logger: Логгер
        method: HTTP метод
        url: URL запроса
        status_code: Код ответа
        duration: Время выполнения в секундах
        user_agent: User-Agent заголовок
        client_ip: IP адрес клиента
        **kwargs: Дополнительные поля для логирования
    """
    log_data = {
        "event": "http_request",
        "method": method,
        "url": url,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2),
        **kwargs
    }
    
    if user_agent:
        log_data["user_agent"] = user_agent
    
    if client_ip:
        log_data["client_ip"] = client_ip
    
    # Выбираем уровень логирования на основе статус кода
    if status_code >= 500:
        logger.error(**log_data)
    elif status_code >= 400:
        logger.warning(**log_data)
    else:
        logger.info(**log_data)


def log_error(
    logger: structlog.BoundLogger,
    error: Exception,
    context: Dict[str, Any] = None,
    **kwargs: Any
) -> None:
    """
    Логирование ошибок
    
    Args:
        logger: Логгер
        error: Объект исключения
        context: Контекст ошибки
        **kwargs: Дополнительные поля для логирования
    """
    log_data = {
        "event": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        **kwargs
    }
    
    if context:
        log_data["context"] = context
    
    logger.error(**log_data, exc_info=True)


def log_business_event(
    logger: structlog.BoundLogger,
    event: str,
    user_id: str = None,
    **kwargs: Any
) -> None:
    """
    Логирование бизнес-событий
    
    Args:
        logger: Логгер
        event: Название события
        user_id: ID пользователя
        **kwargs: Дополнительные поля события
    """
    log_data = {
        "event": event,
        **kwargs
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    logger.info(**log_data)


# Примеры использования:
# logger = get_logger(__name__)
# log_request(logger, "GET", "/api/v1/calculate", 200, 0.5)
# log_error(logger, ValueError("Invalid input"), {"input": "test"})
# log_business_event(logger, "calculation_requested", user_id="123", weight=100)
