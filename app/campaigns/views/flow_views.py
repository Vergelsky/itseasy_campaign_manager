"""
Views для управления потоками (streams)
"""
from django.views import View
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from ..models import Campaign, Flow
from ..services import KeitaroSyncService


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

