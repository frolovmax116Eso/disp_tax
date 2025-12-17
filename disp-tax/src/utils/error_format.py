"""Utility for safe error message formatting."""


def format_error_for_user(error: Exception, max_length: int = 100) -> str:
    """
    Форматирует ошибку для безопасного отображения пользователю.
    
    Args:
        error: Исключение
        max_length: Максимальная длина сообщения
        
    Returns:
        Безопасное сообщение об ошибке
    """
    error_msg = str(error)
    
    # Обрезаем длинные сообщения
    if len(error_msg) > max_length:
        error_msg = error_msg[:max_length] + "..."
    
    # Убираем технические детали для пользователя
    if "no such table" in error_msg.lower():
        return "База данных не инициализирована. Обратитесь к администратору."
    elif "operationalerror" in error_msg.lower():
        return "Ошибка базы данных. Обратитесь к администратору."
    elif "message_too_long" in error_msg.lower():
        return "Сообщение слишком длинное. Попробуйте еще раз."
    elif "bad request" in error_msg.lower():
        return "Ошибка запроса. Попробуйте еще раз."
    
    return error_msg

