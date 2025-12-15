"""
Сервис для синхронизации данных между БД и Keitaro
"""
from typing import Dict, List, Any
from django.conf import settings
from django.db import transaction
from ..models import Campaign, Flow, Offer, FlowOffer
from config.exceptions import KeitaroAPIException
from .client import KeitaroClient
from .calculator import ShareCalculator


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
        
        Кампании, которых нет в Keitaro, помечаются как 'deleted'.
        
        Returns:
            Количество синхронизированных кампаний
        """
        try:
            campaigns_data = self.client.get_campaigns()
            
            # Получаем список всех keitaro_id из Keitaro
            keitaro_campaign_ids = {camp_data['id'] for camp_data in campaigns_data}
            
            synced_count = 0
            for camp_data in campaigns_data:
                keitaro_id = camp_data['id']
                
                # Проверяем, существует ли кампания с таким keitaro_id
                try:
                    existing_campaign = Campaign.objects.get(keitaro_id=keitaro_id)
                    # Если кампания существует, обновляем её данные
                    existing_campaign.name = camp_data.get('name', '')
                    existing_campaign.alias = camp_data.get('alias', '')
                    existing_campaign.state = camp_data.get('state', 'active')
                    existing_campaign.type = camp_data.get('type', 'position')
                    existing_campaign.save()
                except Campaign.DoesNotExist:
                    # Кампания не существует - создаём новую
                    Campaign.objects.create(
                        keitaro_id=keitaro_id,
                        name=camp_data.get('name', ''),
                        alias=camp_data.get('alias', ''),
                        state=camp_data.get('state', 'active'),
                        type=camp_data.get('type', 'position'),
                    )
                
                synced_count += 1
            
            # Помечаем как 'deleted' все кампании, которых нет в Keitaro
            deleted_campaigns = Campaign.objects.exclude(keitaro_id__in=keitaro_campaign_ids)
            deleted_count = deleted_campaigns.update(state='deleted')
            
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
    
    def _update_flow_offer(self, flow: Flow, offer: Offer, offer_data: Dict) -> FlowOffer:
        """
        Вспомогательный метод для обновления или создания FlowOffer
        
        Args:
            flow: Объект Flow
            offer: Объект Offer
            offer_data: Данные оффера из Keitaro API
        
        Returns:
            Объект FlowOffer
        """
        flow_offer, created = FlowOffer.objects.get_or_create(
            flow=flow,
            offer=offer,
            defaults={
                'share': offer_data.get('share', 0),
                'state': offer_data.get('state', 'active'),
                'keitaro_offer_stream_id': offer_data.get('id'),
                'is_pinned': False,
            }
        )
        if not created:
            flow_offer.share = offer_data.get('share', 0)
            flow_offer.keitaro_offer_stream_id = offer_data.get('id')
            
            # Если оффер приходит из Keitaro как активный, активируем его (даже если у нас он disabled)
            keitaro_state = offer_data.get('state', 'active')
            if keitaro_state == 'active':
                flow_offer.state = 'active'
                flow_offer.save(update_fields=['share', 'state', 'keitaro_offer_stream_id'])
            else:
                # Если в Keitaro оффер не активен, сохраняем его состояние только если у нас он тоже не disabled
                # (disabled офферы остаются disabled, если в Keitaro они тоже не активны)
                if flow_offer.state != 'disabled':
                    flow_offer.state = keitaro_state
                    flow_offer.save(update_fields=['share', 'state', 'keitaro_offer_stream_id'])
                else:
                    # Если у нас disabled, а в Keitaro тоже не активен - сохраняем только share и id
                    flow_offer.save(update_fields=['share', 'keitaro_offer_stream_id'])
        return flow_offer
    
    def _sync_flow_offers(self, flow: Flow, offers_data: List[Dict]):
        """
        Синхронизация офферов потока
        
        При синхронизации сохраняются закрепления (is_pinned) существующих офферов,
        так как закрепление - это локальная функция, которая не синхронизируется с Keitaro.
        Новые офферы создаются с is_pinned=False.
        
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
        
        # Помечаем как disabled активные офферы, которых нет в новых данных из Keitaro
        # Это означает, что они были удалены в Keitaro
        current_offer_stream_ids = [o.get('id') for o in offers_data if o.get('id')]
        removed_offers = FlowOffer.objects.filter(
            flow=flow, 
            state='active'
        ).exclude(
            keitaro_offer_stream_id__in=current_offer_stream_ids
        )
        
        # Помечаем их как disabled вместо удаления
        if removed_offers.exists():
            removed_offers.update(state='disabled', share=0)
        
        # Создаём/обновляем связи (используем share из Keitaro)
        for offer_data in offers_data:
            offer_id = offer_data.get('offer_id')
            if not offer_id:
                continue
            
            try:
                offer = Offer.objects.get(keitaro_id=offer_id)
            except Offer.DoesNotExist:
                offer = Offer.objects.create(
                    keitaro_id=offer_id,
                    user=self.user,
                    name=f"Offer {offer_id}",
                    state='active'
                )
            
            self._update_flow_offer(flow, offer, offer_data)
    
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
            
            # Удалённые офферы (state='disabled') остаются в базе для возможности восстановления
            # Они не отправляются в Keitaro, но сохраняются локально
            
            return True
            
        except (KeitaroAPIException, ValueError) as e:
            raise Exception(f'Ошибка отправки в Keitaro: {str(e)}')
    
    def compare_with_keitaro(self, flow: Flow) -> Dict[str, Any]:
        """
        Сравнение локальных данных потока с Keitaro
        
        Disabled офферы не учитываются при сравнении, так как они не синхронизируются с Keitaro.
        
        Args:
            flow: Объект Flow
        
        Returns:
            Dict с информацией о расхождениях
        """
        try:
            stream_data = self.client.get_stream(flow.keitaro_id)
            
            # Получаем только активные локальные офферы (disabled не учитываются)
            local_offers = {
                fo.offer.keitaro_id: fo.share
                for fo in flow.flow_offers.filter(state='active')
            }
            
            # Получаем только активные офферы из Keitaro
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

