"""
Views для управления офферами в потоках
"""
from django.views import View
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from ..models import Flow, Offer, FlowOffer
from ..services import ShareCalculator


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


class RestoreOfferView(View):
    """AJAX: Восстановление удалённого оффера"""
    
    def post(self, request, pk):
        try:
            flow_offer = get_object_or_404(FlowOffer, pk=pk)
            flow = flow_offer.flow
            
            with transaction.atomic():
                # Восстанавливаем FlowOffer
                flow_offer.state = 'active'
                flow_offer.save(update_fields=['state'])
                
                # Пересчитываем share для всех активных офферов
                flow_offers = list(flow.flow_offers.filter(state='active'))
                if flow_offers:
                    new_shares = ShareCalculator.recalculate_shares(flow_offers)
                    
                    for fo in flow_offers:
                        fo.share = new_shares[fo.id]
                        fo.save(update_fields=['share'])
                    
                    # Формируем all_shares для всех активных офферов
                    all_shares = {fo.id: fo.share for fo in flow_offers}
                else:
                    all_shares = {}
            
            return JsonResponse({
                'success': True,
                'message': 'Оффер восстановлен',
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

