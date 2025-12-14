from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    # Список кампаний
    path('', views.CampaignListView.as_view(), name='campaign_list'),
    
    # Детали кампании
    path('<int:pk>/', views.CampaignDetailView.as_view(), name='campaign_detail'),
    
    # AJAX endpoints для синхронизации
    path('<int:pk>/fetch-streams/', views.FetchStreamsView.as_view(), name='fetch_streams'),
    path('<int:pk>/check-sync/', views.CheckSyncView.as_view(), name='check_sync'),
    path('sync-campaigns/', views.SyncCampaignsView.as_view(), name='sync_campaigns'),
    
    # AJAX endpoints для управления офферами
    path('flow/<int:flow_id>/add-offer/', views.AddOfferView.as_view(), name='add_offer'),
    path('flow-offer/<int:pk>/remove/', views.RemoveOfferView.as_view(), name='remove_offer'),
    path('flow-offer/<int:pk>/toggle-pin/', views.TogglePinView.as_view(), name='toggle_pin'),
    path('flow/<int:flow_id>/push/', views.PushToKeitaroView.as_view(), name='push_to_keitaro'),
    path('flow/<int:flow_id>/cancel/', views.CancelChangesView.as_view(), name='cancel_changes'),
    
    # Автодополнение офферов
    path('offers/autocomplete/', views.OfferAutocompleteView.as_view(), name='offer_autocomplete'),
    
    # Статистика
    path('stats/', views.CampaignStatsAPIView.as_view(), name='campaign_stats'),
]

