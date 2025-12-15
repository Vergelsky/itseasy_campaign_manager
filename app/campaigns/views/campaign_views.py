"""
Views для управления кампаниями
"""
from django.views.generic import ListView, DetailView
from django.views import View
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Count
from django.conf import settings
from ..models import Campaign, Offer
from ..services import KeitaroSyncService, KeitaroClient
from ..forms import CreateCampaignForm
from config.exceptions import KeitaroAPIException


class CampaignListView(ListView):
    """Список рекламных кампаний"""
    model = Campaign
    template_name = 'campaigns/campaign_list.html'
    context_object_name = 'campaigns'
    paginate_by = 50
    
    def get_queryset(self):
        """Получение всех активных кампаний (исключая удалённые)"""
        return Campaign.objects.exclude(state='deleted').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем количество потоков для каждой кампании
        for campaign in context['campaigns']:
            campaign.flows_count = campaign.flows.count()
        return context


class CampaignDetailView(DetailView):
    """Детальная страница кампании с потоками"""
    model = Campaign
    template_name = 'campaigns/campaign_detail.html'
    context_object_name = 'campaign'
    
    def get_queryset(self):
        """Все активные кампании (исключая удалённые)"""
        return Campaign.objects.exclude(state='deleted')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Сортируем потоки: сначала по количеству офферов (убывание), затем по position
        flows = self.object.flows.prefetch_related('flow_offers__offer').annotate(
            offers_count=Count('flow_offers')
        ).order_by('-offers_count', 'position')
        context['flows'] = flows
        return context


class CreateCampaignView(View):
    """AJAX: Создание новой рекламной кампании"""
    
    def post(self, request):
        try:
            form = CreateCampaignForm(request.POST)
            
            if not form.is_valid():
                errors = form.errors.as_json()
                return JsonResponse({'success': False, 'error': 'Ошибка валидации формы', 'errors': errors}, status=400)
            
            name = form.cleaned_data['name']
            geo_codes_str = form.cleaned_data['geo_codes']
            offer_id = form.cleaned_data['offer_id']
            
            # Парсим гео-коды
            geo_codes = [code.strip().upper() for code in geo_codes_str.split(',') if code.strip()]
            if not geo_codes:
                return JsonResponse({'success': False, 'error': 'Укажите хотя бы один гео-код страны'}, status=400)
            
            # Получаем оффер
            try:
                offer = Offer.objects.get(keitaro_id=offer_id, user=request.user)
            except Offer.DoesNotExist:
                # Если оффер не найден в кэше, синхронизируем
                sync_service = KeitaroSyncService(request.user)
                sync_service.sync_offers()
                try:
                    offer = Offer.objects.get(keitaro_id=offer_id, user=request.user)
                except Offer.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Оффер не найден'}, status=400)
            
            # Получаем клиент Keitaro
            keitaro_url = getattr(settings, 'KEITARO_URL', '')
            if not keitaro_url:
                return JsonResponse({'success': False, 'error': 'KEITARO_URL не настроен'}, status=500)
            
            client = KeitaroClient(keitaro_url, request.user.api_key)
            
            with transaction.atomic():
                # Создаём кампанию в Keitaro
                campaign_data = client.create_campaign(name)
                campaign_keitaro_id = campaign_data['id']
                
                # Формируем название для первого потока: "US,GB,DE → Google"
                geo_codes_str = ', '.join(geo_codes[:3])  # Первые 3 кода для краткости
                if len(geo_codes) > 3:
                    geo_codes_str += f' +{len(geo_codes) - 3}'
                stream1_name = f'{geo_codes_str} → Google'
                
                # Создаём первый поток: гео-таргетинг на указанные страны, редирект на Google
                # Фильтр использует name='country' (не 'country_code')
                geo_filters = [{
                    'name': 'country',
                    'mode': 'accept',
                    'payload': geo_codes
                }]
                
                client.create_stream(
                    campaign_id=campaign_keitaro_id,
                    name=stream1_name,
                    action_type='http',
                    schema='redirect',
                    stream_type='regular',
                    action_payload='',  # Пустая строка для redirect
                    action_options={'url': 'https://www.google.com'},  # URL в action_options
                    filters=geo_filters,
                    position=0
                )
                
                # Создаём второй поток: редирект на оффер
                # Используем schema='landings', action_type='campaign', type='forced'
                client.create_stream(
                    campaign_id=campaign_keitaro_id,
                    name='All → Offers',
                    action_type='campaign',
                    schema='landings',
                    stream_type='forced',
                    action_payload='',  # Пустая строка
                    action_options=None,
                    filters=[],  # Без фильтров - ловит всех
                    offers=[{
                        'offer_id': offer_id,
                        'share': 100,  # 100% на один оффер
                        'state': 'active'
                    }],
                    position=1
                )
                
                # Сохраняем кампанию в локальную БД
                campaign = Campaign.objects.create(
                    keitaro_id=campaign_keitaro_id,
                    name=campaign_data.get('name', name),
                    alias=campaign_data.get('alias', ''),
                    state=campaign_data.get('state', 'active')
                )
            
            return JsonResponse({
                'success': True,
                'message': f'Кампания "{name}" успешно создана',
                'campaign_id': campaign.id,
                'auto_fetch': True  # Флаг для автоматического fetch streams
            })
            
        except KeitaroAPIException as e:
            return JsonResponse({'success': False, 'error': f'Ошибка Keitaro API: {str(e)}'}, status=500)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Ошибка при создании кампании: {str(e)}'}, status=500)

