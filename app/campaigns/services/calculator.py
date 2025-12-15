"""
Калькулятор для пересчёта share офферов в потоке
"""
from typing import Dict, List, Optional
from django.conf import settings
from ..models import FlowOffer

# Минимальный процент share для незакреплённых офферов
MIN_SHARE_PERCENT = getattr(settings, 'MIN_SHARE_PERCENT', 1)


class ShareCalculator:
    """Калькулятор для пересчёта share офферов в потоке"""
    
    @staticmethod
    def recalculate_shares(flow_offers: List[FlowOffer]) -> Dict[int, int]:
        """
        Пересчёт share для офферов в потоке
        
        Правила:
        - Сумма всех share должна быть 100%
        - Зафиксированные (pinned) share не изменяются
        - Незафиксированные делятся равномерно на оставшиеся проценты
        
        Args:
            flow_offers: Список FlowOffer объектов
        
        Returns:
            Dict с новыми значениями {flow_offer_id: new_share}
        """
        if not flow_offers:
            return {}
        
        # Разделяем на зафиксированные и незафиксированные
        pinned = [fo for fo in flow_offers if fo.is_pinned and fo.state == 'active']
        unpinned = [fo for fo in flow_offers if not fo.is_pinned and fo.state == 'active']
        
        # Сумма зафиксированных
        pinned_sum = sum(fo.share for fo in pinned)
        
        # Проверка: сумма зафиксированных не может быть >= 100
        if pinned_sum >= 100:
            raise ValueError('Сумма зафиксированных share >= 100%')
        
        # Доступные проценты для распределения
        available = 100 - pinned_sum
        
        # Если нет незафиксированных, ничего не делаем
        if not unpinned:
            return {fo.id: fo.share for fo in pinned}
        
        # Равномерное распределение
        base_share = available // len(unpinned)
        remainder = available % len(unpinned)
        
        # Проверка: минимум MIN_SHARE_PERCENT% на оффер если возможно
        if base_share < MIN_SHARE_PERCENT and available >= len(unpinned) * MIN_SHARE_PERCENT:
            base_share = MIN_SHARE_PERCENT
            remainder = available - (base_share * len(unpinned))
        
        result = {}
        
        # Зафиксированные не меняются
        for fo in pinned:
            result[fo.id] = fo.share
        
        # Распределяем между незафиксированными
        for i, fo in enumerate(unpinned):
            # Первым офферам добавляем остаток
            extra = 1 if i < remainder else 0
            result[fo.id] = base_share + extra
        
        return result
    
    @staticmethod
    def validate_shares(flow_offers: List[FlowOffer]) -> tuple[bool, Optional[str]]:
        """
        Валидация share в потоке
        
        Args:
            flow_offers: Список FlowOffer объектов
        
        Returns:
            (is_valid, error_message)
        """
        if not flow_offers:
            return True, None
        
        active_offers = [fo for fo in flow_offers if fo.state == 'active']
        
        if not active_offers:
            return True, None
        
        # Проверка суммы
        total = sum(fo.share for fo in active_offers)
        if total != 100:
            return False, f'Сумма share должна быть 100%, текущая: {total}%'
        
        # Проверка минимума
        for fo in active_offers:
            if fo.share < 0:
                return False, f'Share не может быть отрицательным'
            if fo.share > 100:
                return False, f'Share не может быть больше 100%'
        
        return True, None

