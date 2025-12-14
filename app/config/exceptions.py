"""
Кастомные исключения для приложения
"""


class KeitaroAPIException(Exception):
    """Базовое исключение для ошибок API Keitaro"""
    pass


class KeitaroAuthException(KeitaroAPIException):
    """Исключение для ошибок аутентификации (неверный API ключ)"""
    pass


class KeitaroConnectionException(KeitaroAPIException):
    """Исключение для ошибок подключения к Keitaro (сервис недоступен)"""
    pass

