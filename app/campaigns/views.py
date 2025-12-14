from django.views.generic import ListView, DetailView
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Case, When, IntegerField
from .models import Campaign, Flow, Offer, FlowOffer
from .services import KeitaroSyncService, ShareCalculator
from config.exceptions import KeitaroAPIException


class CampaignListView(ListView):
    """Список рекламных кампаний"""
    model = Campaign
    template_name = 'campaigns/campaign_list.html'
    context_object_name = 'campaigns'
    paginate_by = 50
    
    def get_queryset(self):
        """Получение всех кампаний"""
        return Campaign.objects.all().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем количество потоков для каждой кампании
        for campaign in context['campaigns']:
            campaign.flows_count = campaign.flows.count()
        return context


class SyncCampaignsView(View):
    """AJAX: Синхронизация кампаний из Keitaro"""
    
    def post(self, request):
        try:
            sync_service = KeitaroSyncService(request.user)
            count = sync_service.sync_campaigns()
            
            return JsonResponse({
                'success': True,
                'message': f'Синхронизировано кампаний: {count}',
                'count': count,
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=500)


class CampaignDetailView(DetailView):
    """Детальная страница кампании с потоками"""
    model = Campaign
    template_name = 'campaigns/campaign_detail.html'
    context_object_name = 'campaign'
    
    def get_queryset(self):
        """Все кампании"""
        return Campaign.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Сортируем потоки: сначала по количеству офферов (убывание), затем по position
        flows = self.object.flows.prefetch_related('flow_offers__offer').annotate(
            offers_count=Count('flow_offers')
        ).order_by('-offers_count', 'position')
        context['flows'] = flows
        return context


class FetchStreamsView(View):
    """AJAX: Синхронизация потоков кампании из Keitaro"""
    
    def post(self, request, pk):
        try:
            campaign = get_object_or_404(Campaign, pk=pk)
            sync_service = KeitaroSyncService(request.user)
            count = sync_service.sync_streams(campaign)
            
            return JsonResponse({
                'success': True,
                'message': f'Синхронизировано потоков: {count}',
                'count': count,
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=500)


class CheckSyncView(View):
    """AJAX: Проверка расхождений с Keitaro"""
    
    def get(self, request, pk):
        try:
            campaign = get_object_or_404(Campaign, pk=pk)
            sync_service = KeitaroSyncService(request.user)
            
            differences = []
            for flow in campaign.flows.all():
                result = sync_service.compare_with_keitaro(flow)
                if result.get('has_differences'):
                    differences.append({
                        'flow_id': flow.id,
                        'flow_name': flow.name,
                        'local': result.get('local_offers'),
                        'keitaro': result.get('keitaro_offers'),
                    })
            
            return JsonResponse({
                'success': True,
                'has_differences': len(differences) > 0,
                'differences': differences,
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=500)


class AddOfferView(View):
    """AJAX: Добавление оффера в поток"""
    
    def post(self, request, flow_id):
        try:
            flow = get_object_or_404(Flow, pk=flow_id)
            offer_id = request.POST.get('offer_id')
            
            if not offer_id:
                return JsonResponse({'success': False, 'error': 'Не указан offer_id'}, status=400)
            
            offer = get_object_or_404(Offer, keitaro_id=offer_id, user=request.user)
            
            # Проверяем что оффер ещё не добавлен
            if FlowOffer.objects.filter(flow=flow, offer=offer).exists():
                return JsonResponse({'success': False, 'error': 'Оффер уже добавлен в этот поток'}, status=400)
            
            with transaction.atomic():
                # Создаём новый FlowOffer
                flow_offer = FlowOffer.objects.create(
                    flow=flow,
                    offer=offer,
                    share=0,
                    state='active'
                )
                
                # Пересчитываем share
                flow_offers = list(flow.flow_offers.filter(state='active'))
                new_shares = ShareCalculator.recalculate_shares(flow_offers)
                
                # Обновляем share для всех офферов
                updated_shares = {}
                for fo in flow_offers:
                    fo.share = new_shares[fo.id]
                    fo.save(update_fields=['share'])
                    updated_shares[fo.id] = fo.share
            
            return JsonResponse({
                'success': True,
                'message': 'Оффер добавлен',
                'flow_offer_id': flow_offer.id,
                'offer_name': offer.name,
                'share': flow_offer.share,
                'all_shares': updated_shares,
            })
            
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class RemoveOfferView(View):
    """AJAX: Удаление оффера из потока"""
    
    def post(self, request, pk):
        try:
            flow_offer = get_object_or_404(FlowOffer, pk=pk)
            flow = flow_offer.flow
            
            with transaction.atomic():
                # Помечаем FlowOffer как disabled вместо удаления
                flow_offer.state = 'disabled'
                flow_offer.share = 0
                flow_offer.save(update_fields=['state', 'share'])
                
                # Пересчитываем share для оставшихся активных
                flow_offers = list(flow.flow_offers.filter(state='active'))
                if flow_offers:
                    new_shares = ShareCalculator.recalculate_shares(flow_offers)
                    
                    for fo in flow_offers:
                        fo.share = new_shares[fo.id]
                        fo.save(update_fields=['share'])
                
                # Формируем all_shares включая удалённый оффер с share=0
                all_shares = {fo.id: fo.share for fo in flow_offers}
                all_shares[flow_offer.id] = 0  # Добавляем удалённый оффер с share=0
            
            return JsonResponse({
                'success': True,
                'message': 'Оффер помечен для удаления',
                'all_shares': all_shares,
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class TogglePinView(View):
    """AJAX: Переключение закрепления оффера"""
    
    def post(self, request, pk):
        try:
            flow_offer = get_object_or_404(FlowOffer, pk=pk)
            flow = flow_offer.flow
            
            with transaction.atomic():
                # Переключаем состояние закрепления
                flow_offer.is_pinned = not flow_offer.is_pinned
                flow_offer.save(update_fields=['is_pinned'])
                
                # Пересчитываем share для незакреплённых офферов
                flow_offers = list(flow.flow_offers.filter(state='active'))
                new_shares = ShareCalculator.recalculate_shares(flow_offers)
                
                # Обновляем share для всех офферов (закреплённые не меняются в recalculate_shares)
                updated_shares = {}
                for fo in flow_offers:
                    fo.share = new_shares[fo.id]
                    fo.save(update_fields=['share'])
                    updated_shares[fo.id] = fo.share
                
                # Валидация
                is_valid, error = ShareCalculator.validate_shares(flow_offers)
                
                if not is_valid:
                    return JsonResponse({
                        'success': False,
                        'error': error,
                        'is_valid': False,
                    }, status=400)
            
            return JsonResponse({
                'success': True,
                'message': 'Состояние закрепления изменено',
                'is_pinned': flow_offer.is_pinned,
                'all_shares': updated_shares,
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class PushToKeitaroView(View):
    """AJAX: Отправка изменений в Keitaro"""
    
    def post(self, request, flow_id):
        try:
            flow = get_object_or_404(Flow, pk=flow_id)
            sync_service = KeitaroSyncService(request.user)
            
            sync_service.push_stream_offers(flow)
            
            return JsonResponse({
                'success': True,
                'message': 'Изменения отправлены в Keitaro',
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class CancelChangesView(View):
    """AJAX: Отмена изменений (reload потока из Keitaro)"""
    
    def post(self, request, flow_id):
        try:
            flow = get_object_or_404(Flow, pk=flow_id)
            sync_service = KeitaroSyncService(request.user)
            
            # Возвращаем disabled офферы в active перед синхронизацией
            flow.flow_offers.filter(state='disabled').update(state='active')
            
            # Перезагружаем данные из Keitaro
            sync_service.sync_streams(flow.campaign)
            
            return JsonResponse({
                'success': True,
                'message': 'Изменения отменены',
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class OfferAutocompleteView(View):
    """AJAX: Автодополнение офферов"""
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({'results': []})
        
        # Поиск по кэшу офферов
        offers = Offer.objects.filter(
            user=request.user,
            name__icontains=query,
            state='active'
        ).order_by('name')[:20]
        
        results = [{
            'id': offer.keitaro_id,
            'name': offer.name,
        } for offer in offers]
        
        return JsonResponse({'results': results})


class CampaignStatsAPIView(View):
    """AJAX: Получение статистики кампаний через Keitaro report API"""
    
    def post(self, request):
        try:
            campaign_ids = request.POST.getlist('campaign_ids[]')
            
            if not campaign_ids:
                return JsonResponse({'success': False, 'error': 'Не указаны campaign_ids'}, status=400)
            
            # Получаем кампании
            campaigns = Campaign.objects.filter(
                id__in=campaign_ids
            )
            
            sync_service = KeitaroSyncService(request.user)
            
            # Формируем параметры отчёта
            # Получаем статистику за последние 30 дней
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Собираем keitaro_ids кампаний
            keitaro_campaign_ids = [c.keitaro_id for c in campaigns]
            
            report_params = {
                'range': {
                    'from': start_date.strftime('%Y-%m-%d'),
                    'to': end_date.strftime('%Y-%m-%d'),
                    'timezone': 'UTC'
                },
                'columns': ['campaign_id'],
                'metrics': [
                    'clicks',
                    'conversions', 
                    'sales',
                    'cr',
                    'crs',
                    'revenue',
                    'cost',
                    'profit',
                    'roi'
                ],
                'filters': [
                    {
                        'name': 'campaign_id',
                        'operator': 'IN_LIST',
                        'expression': keitaro_campaign_ids
                    }
                ]
            }
            
            try:
                report_data = sync_service.client.get_report(report_params)
                
                # Преобразуем данные в удобный формат
                stats = {}
                
                if 'rows' in report_data:
                    for row in report_data['rows']:
                        camp_keitaro_id = row.get('campaign_id')
                        # Находим campaign по keitaro_id
                        campaign = campaigns.filter(keitaro_id=camp_keitaro_id).first()
                        if campaign:
                            stats[str(campaign.id)] = {
                                'clicks': row.get('clicks', 0),
                                'conversions': row.get('conversions', 0),
                                'sales': row.get('sales', 0),
                                'cr': round(row.get('cr', 0), 2),
                                'revenue': round(row.get('revenue', 0), 2),
                                'cost': round(row.get('cost', 0), 2),
                                'profit': round(row.get('profit', 0), 2),
                                'roi': round(row.get('roi', 0), 2),
                            }
                
                # Для кампаний без данных возвращаем нули
                for campaign in campaigns:
                    if str(campaign.id) not in stats:
                        stats[str(campaign.id)] = {
                            'clicks': 0,
                            'conversions': 0,
                            'sales': 0,
                            'cr': 0,
                            'revenue': 0,
                            'cost': 0,
                            'profit': 0,
                            'roi': 0,
                        }
                
                return JsonResponse({
                    'success': True,
                    'stats': stats,
                })
                
            except KeitaroAPIException as e:
                # Если не удалось получить статистику, возвращаем нули
                stats = {}
                for campaign in campaigns:
                    stats[str(campaign.id)] = {
                        'clicks': 0,
                        'conversions': 0,
                        'sales': 0,
                        'cr': 0,
                        'revenue': 0,
                        'cost': 0,
                        'profit': 0,
                        'roi': 0,
                    }
                
                return JsonResponse({
                    'success': True,
                    'stats': stats,
                    'warning': 'Не удалось загрузить статистику: ' + str(e)
                })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
