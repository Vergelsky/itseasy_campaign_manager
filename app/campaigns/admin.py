from django.contrib import admin
from .models import Campaign, Flow, Offer, FlowOffer


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """Админ-панель для модели Campaign"""
    
    list_display = ('id', 'name', 'keitaro_id', 'state', 'type', 'synced_at')
    list_filter = ('state', 'type', 'synced_at')
    search_fields = ('name', 'alias', 'keitaro_id')
    readonly_fields = ('keitaro_id', 'synced_at', 'created_at')
    list_per_page = 50
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'alias', 'state', 'type')
        }),
        ('Keitaro', {
            'fields': ('keitaro_id', 'synced_at')
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    """Админ-панель для модели Flow"""
    
    list_display = ('id', 'name', 'campaign', 'keitaro_id', 'type', 'position', 'state', 'synced_at')
    list_filter = ('type', 'state', 'synced_at')
    search_fields = ('name', 'keitaro_id', 'campaign__name')
    readonly_fields = ('keitaro_id', 'synced_at', 'created_at')
    list_per_page = 50
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('campaign', 'name', 'type', 'position', 'state')
        }),
        ('Keitaro', {
            'fields': ('keitaro_id', 'synced_at')
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Админ-панель для модели Offer"""
    
    list_display = ('id', 'name', 'keitaro_id', 'user', 'state', 'cached_at')
    list_filter = ('state', 'user', 'cached_at')
    search_fields = ('name', 'keitaro_id')
    readonly_fields = ('keitaro_id', 'cached_at', 'created_at')
    list_per_page = 50
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'name', 'state')
        }),
        ('Keitaro', {
            'fields': ('keitaro_id', 'cached_at')
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(FlowOffer)
class FlowOfferAdmin(admin.ModelAdmin):
    """Админ-панель для модели FlowOffer"""
    
    list_display = ('id', 'flow', 'offer', 'share', 'is_pinned', 'state', 'updated_at')
    list_filter = ('state', 'is_pinned')
    search_fields = ('flow__name', 'offer__name')
    readonly_fields = ('keitaro_offer_stream_id', 'created_at', 'updated_at')
    list_per_page = 50
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('flow', 'offer', 'share', 'is_pinned', 'state')
        }),
        ('Keitaro', {
            'fields': ('keitaro_offer_stream_id',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
