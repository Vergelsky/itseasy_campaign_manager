"""
Views для получения статистики кампаний
"""
from django.views import View
from django.http import JsonResponse
from datetime import datetime, timedelta
from ..models import Campaign
from ..services import KeitaroSyncService
from config.exceptions import KeitaroAPIException


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

