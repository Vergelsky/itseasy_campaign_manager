"""
Сервисы для работы с Keitaro API и бизнес-логикой
"""
import requests
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.db import transaction
from .models import Campaign, Flow, Offer, FlowOffer


class KeitaroAPIException(Exception):
    """Исключение для ошибок API Keitaro"""
    pass


class KeitaroClient:
    """Клиент для работы с Keitaro API"""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Инициализация клиента
        
        Args:
            base_url: URL Keitaro инстанса
            api_key: API ключ для аутентификации
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_base = f"{self.base_url}/admin_api/v1"
        self.headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json',
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Выполнение HTTP запроса к API
        
        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: API endpoint (без /admin_api/v1)
            **kwargs: Дополнительные параметры для requests
        
        Returns:
            JSON ответ от API
        
        Raises:
            KeitaroAPIException: При ошибках API
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            
            # Обработка ошибок
            if response.status_code == 401:
                raise KeitaroAPIException('Неверный API ключ или доступ запрещён')
            elif response.status_code == 404:
                raise KeitaroAPIException(f'Ресурс не найден: {endpoint}')
            elif response.status_code >= 500:
                raise KeitaroAPIException(f'Ошибка сервера Keitaro: {response.status_code}')
            elif response.status_code >= 400:
                raise KeitaroAPIException(f'Ошибка запроса: {response.status_code} - {response.text}')
            
            response.raise_for_status()
            
            # Некоторые endpoints возвращают пустой ответ
            if not response.content:
                return {}
            
            return response.json()
            
        except requests.exceptions.Timeout:
            raise KeitaroAPIException('Превышено время ожидания ответа от Keitaro')
        except requests.exceptions.ConnectionError:
            raise KeitaroAPIException('Не удалось подключиться к Keitaro')
        except requests.exceptions.RequestException as e:
            raise KeitaroAPIException(f'Ошибка при запросе к Keitaro: {str(e)}')
    
    def get_campaigns(self, offset: int = 0, limit: int = 100) -> List[Dict]:
        """
        Получение списка кампаний
        
        Args:
            offset: Смещение для пагинации
            limit: Количество записей
        
        Returns:
            Список кампаний
        """
        params = {}
        if offset:
            params['offset'] = offset
        if limit:
            params['limit'] = limit
        
        return self._make_request('GET', 'campaigns', params=params)
    
    def get_campaign(self, campaign_id: int) -> Dict:
        """
        Получение деталей кампании
        
        Args:
            campaign_id: ID кампании в Keitaro
        
        Returns:
            Данные кампании
        """
        return self._make_request('GET', f'campaigns/{campaign_id}')
    
    def get_streams(self, campaign_id: int) -> List[Dict]:
        """
        Получение потоков (streams) кампании
        
        Args:
            campaign_id: ID кампании в Keitaro
        
        Returns:
            Список потоков с офферами
        """
        return self._make_request('GET', f'campaigns/{campaign_id}/streams')
    
    def get_stream(self, stream_id: int) -> Dict:
        """
        Получение деталей потока
        
        Args:
            stream_id: ID потока в Keitaro
        
        Returns:
            Данные потока
        """
        return self._make_request('GET', f'streams/{stream_id}')
    
    def update_stream(self, stream_id: int, data: Dict) -> Dict:
        """
        Обновление потока (включая offers)
        
        Args:
            stream_id: ID потока в Keitaro
            data: Данные для обновления
        
        Returns:
            Обновлённые данные потока
        """
        return self._make_request('PUT', f'streams/{stream_id}', json=data)
    
    def get_offers(self) -> List[Dict]:
        """
        Получение списка всех офферов
        
        Returns:
            Список офферов
        """
        return self._make_request('GET', 'offers')
    
    def get_report(self, params: Dict) -> Dict:
        """
        Построение отчёта (для статистики)
        
        Args:
            params: Параметры отчёта (columns, metrics, filters, range)
        
        Returns:
            Данные отчёта
        """
        return self._make_request('POST', 'report/build', json=params)
    
    def validate_api_key(self) -> bool:
        """
        Проверка валидности API ключа
        
        Returns:
            True если ключ валиден, False иначе
        """
        try:
            self.get_campaigns(limit=1)
            return True
        except KeitaroAPIException:
            return False


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
        
        # Проверка: минимум 1% на оффер если возможно
        if base_share < 1 and available >= len(unpinned):
            base_share = 1
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


class KeitaroSyncService:
    """Сервис для синхронизации данных между БД и Keitaro"""
    
    def __init__(self, user):
        """
        Инициализация сервиса
        
        Args:
            user: Объект User с api_key
        """
        self.user = user
        self.client = KeitaroClient(settings.KEITARO_URL, user.api_key)
    
    @transaction.atomic
    def sync_campaigns(self) -> int:
        """
        Синхронизация кампаний из Keitaro в БД
        
        Returns:
            Количество синхронизированных кампаний
        """
        try:
            campaigns_data = self.client.get_campaigns()
            
            synced_count = 0
            for camp_data in campaigns_data:
                campaign, created = Campaign.objects.update_or_create(
                    keitaro_id=camp_data['id'],
                    user=self.user,
                    defaults={
                        'name': camp_data.get('name', ''),
                        'alias': camp_data.get('alias', ''),
                        'state': camp_data.get('state', 'active'),
                        'type': camp_data.get('type', 'position'),
                    }
                )
                synced_count += 1
            
            return synced_count
            
        except KeitaroAPIException as e:
            raise Exception(f'Ошибка синхронизации кампаний: {str(e)}')
    
    @transaction.atomic
    def sync_streams(self, campaign: Campaign) -> int:
        """
        Синхронизация потоков кампании из Keitaro
        
        Args:
            campaign: Объект Campaign
        
        Returns:
            Количество синхронизированных потоков
        """
        try:
            streams_data = self.client.get_streams(campaign.keitaro_id)
            
            synced_count = 0
            for stream_data in streams_data:
                flow, created = Flow.objects.update_or_create(
                    keitaro_id=stream_data['id'],
                    campaign=campaign,
                    defaults={
                        'name': stream_data.get('name', ''),
                        'type': stream_data.get('type', 'offers'),
                        'position': stream_data.get('position', 0),
                        'state': stream_data.get('state', 'active'),
                    }
                )
                
                # Синхронизация офферов потока
                self._sync_flow_offers(flow, stream_data.get('offers', []))
                synced_count += 1
            
            return synced_count
            
        except KeitaroAPIException as e:
            raise Exception(f'Ошибка синхронизации потоков: {str(e)}')
    
    def _sync_flow_offers(self, flow: Flow, offers_data: List[Dict]):
        """
        Синхронизация офферов потока
        
        Args:
            flow: Объект Flow
            offers_data: Список данных офферов из Keitaro
        """
        # Сначала кэшируем офферы если их нет
        offer_ids = [o['offer_id'] for o in offers_data if 'offer_id' in o]
        for offer_id in offer_ids:
            if not Offer.objects.filter(keitaro_id=offer_id).exists():
                # Попробуем получить информацию об оффере
                try:
                    all_offers = self.client.get_offers()
                    for offer_data in all_offers:
                        Offer.objects.update_or_create(
                            keitaro_id=offer_data['id'],
                            user=self.user,
                            defaults={
                                'name': offer_data.get('name', f"Offer {offer_data['id']}"),
                                'state': offer_data.get('state', 'active'),
                            }
                        )
                    break
                except Exception:
                    pass
        
        # Удаляем старые связи, которых нет в новых данных
        current_offer_stream_ids = [o.get('id') for o in offers_data if o.get('id')]
        FlowOffer.objects.filter(flow=flow).exclude(
            keitaro_offer_stream_id__in=current_offer_stream_ids
        ).delete()
        
        # Создаём/обновляем связи
        for offer_data in offers_data:
            offer_id = offer_data.get('offer_id')
            if not offer_id:
                continue
            
            try:
                offer = Offer.objects.get(keitaro_id=offer_id)
                FlowOffer.objects.update_or_create(
                    flow=flow,
                    offer=offer,
                    defaults={
                        'share': offer_data.get('share', 0),
                        'state': offer_data.get('state', 'active'),
                        'keitaro_offer_stream_id': offer_data.get('id'),
                    }
                )
            except Offer.DoesNotExist:
                # Оффер не найден в кэше, создаём placeholder
                offer = Offer.objects.create(
                    keitaro_id=offer_id,
                    user=self.user,
                    name=f"Offer {offer_id}",
                    state='active'
                )
                FlowOffer.objects.update_or_create(
                    flow=flow,
                    offer=offer,
                    defaults={
                        'share': offer_data.get('share', 0),
                        'state': offer_data.get('state', 'active'),
                        'keitaro_offer_stream_id': offer_data.get('id'),
                    }
                )
    
    @transaction.atomic
    def sync_offers(self) -> int:
        """
        Синхронизация офферов (кэш для автодополнения)
        
        Returns:
            Количество синхронизированных офферов
        """
        try:
            offers_data = self.client.get_offers()
            
            synced_count = 0
            for offer_data in offers_data:
                offer, created = Offer.objects.update_or_create(
                    keitaro_id=offer_data['id'],
                    user=self.user,
                    defaults={
                        'name': offer_data.get('name', f"Offer {offer_data['id']}"),
                        'state': offer_data.get('state', 'active'),
                    }
                )
                synced_count += 1
            
            return synced_count
            
        except KeitaroAPIException as e:
            raise Exception(f'Ошибка синхронизации офферов: {str(e)}')
    
    def push_stream_offers(self, flow: Flow) -> bool:
        """
        Отправка изменений офферов потока в Keitaro
        
        Args:
            flow: Объект Flow
        
        Returns:
            True если успешно
        """
        try:
            # Получаем текущие офферы потока
            flow_offers = flow.flow_offers.filter(state='active')
            
            # Валидация
            is_valid, error = ShareCalculator.validate_shares(list(flow_offers))
            if not is_valid:
                raise ValueError(f'Невалидные share: {error}')
            
            # Формируем данные для отправки
            offers_data = []
            for fo in flow_offers:
                offers_data.append({
                    'offer_id': fo.offer.keitaro_id,
                    'share': fo.share,
                    'state': fo.state,
                })
            
            # Отправляем в Keitaro
            update_data = {
                'offers': offers_data
            }
            
            self.client.update_stream(flow.keitaro_id, update_data)
            
            return True
            
        except (KeitaroAPIException, ValueError) as e:
            raise Exception(f'Ошибка отправки в Keitaro: {str(e)}')
    
    def compare_with_keitaro(self, flow: Flow) -> Dict[str, Any]:
        """
        Сравнение локальных данных потока с Keitaro
        
        Args:
            flow: Объект Flow
        
        Returns:
            Dict с информацией о расхождениях
        """
        try:
            stream_data = self.client.get_stream(flow.keitaro_id)
            
            # Получаем локальные офферы
            local_offers = {
                fo.offer.keitaro_id: fo.share
                for fo in flow.flow_offers.filter(state='active')
            }
            
            # Получаем офферы из Keitaro
            keitaro_offers = {
                o['offer_id']: o['share']
                for o in stream_data.get('offers', [])
                if o.get('state') == 'active'
            }
            
            # Сравниваем
            has_differences = local_offers != keitaro_offers
            
            return {
                'has_differences': has_differences,
                'local_offers': local_offers,
                'keitaro_offers': keitaro_offers,
            }
            
        except KeitaroAPIException as e:
            return {
                'error': str(e),
                'has_differences': False,
            }

