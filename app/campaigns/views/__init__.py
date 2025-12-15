"""
Views для управления кампаниями, потоками и офферами
"""
from .campaign_views import CampaignListView, CampaignDetailView, CreateCampaignView
from .flow_views import SyncCampaignsView, FetchStreamsView, CheckSyncView, PushToKeitaroView, CancelChangesView
from .offer_views import AddOfferView, RemoveOfferView, RestoreOfferView, TogglePinView, OfferAutocompleteView
from .stats_views import CampaignStatsAPIView

__all__ = [
    'CampaignListView',
    'CampaignDetailView',
    'CreateCampaignView',
    'SyncCampaignsView',
    'FetchStreamsView',
    'CheckSyncView',
    'PushToKeitaroView',
    'CancelChangesView',
    'AddOfferView',
    'RemoveOfferView',
    'RestoreOfferView',
    'TogglePinView',
    'OfferAutocompleteView',
    'CampaignStatsAPIView',
]

