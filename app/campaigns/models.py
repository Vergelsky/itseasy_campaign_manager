from django.db import models
from django.conf import settings


class Campaign(models.Model):
    """Рекламная кампания из Keitaro"""
    
    keitaro_id = models.IntegerField(unique=True, verbose_name='ID в Keitaro')
    name = models.CharField(max_length=255, verbose_name='Название')
    alias = models.CharField(max_length=255, blank=True, verbose_name='Алиас')
    state = models.CharField(max_length=50, default='active', verbose_name='Состояние')
    type = models.CharField(max_length=50, default='position', verbose_name='Тип')
    synced_at = models.DateTimeField(auto_now=True, verbose_name='Синхронизировано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'Кампания'
        verbose_name_plural = 'Кампании'
        db_table = 'campaigns'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['keitaro_id']),
            models.Index(fields=['state']),
        ]
    
    def __str__(self):
        return f'{self.name} (ID: {self.keitaro_id})'


class Flow(models.Model):
    """Поток (stream) кампании"""
    
    keitaro_id = models.IntegerField(verbose_name='ID в Keitaro')
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='flows',
        verbose_name='Кампания'
    )
    name = models.CharField(max_length=255, verbose_name='Название')
    type = models.CharField(max_length=50, default='offers', verbose_name='Тип потока')
    position = models.IntegerField(default=0, verbose_name='Позиция')
    state = models.CharField(max_length=50, default='active', verbose_name='Состояние')
    synced_at = models.DateTimeField(auto_now=True, verbose_name='Синхронизировано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'Поток'
        verbose_name_plural = 'Потоки'
        db_table = 'flows'
        ordering = ['position']
        unique_together = [['campaign', 'keitaro_id']]
        indexes = [
            models.Index(fields=['campaign', 'state']),
            models.Index(fields=['keitaro_id']),
        ]
    
    def __str__(self):
        return f'{self.name} (Campaign: {self.campaign.name})'


class Offer(models.Model):
    """Оффер (кэшированный из Keitaro)"""
    
    keitaro_id = models.IntegerField(unique=True, verbose_name='ID в Keitaro')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='offers',
        verbose_name='Пользователь'
    )
    name = models.CharField(max_length=255, verbose_name='Название')
    state = models.CharField(max_length=50, default='active', verbose_name='Состояние')
    cached_at = models.DateTimeField(auto_now=True, verbose_name='Кэшировано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'Оффер'
        verbose_name_plural = 'Офферы'
        db_table = 'offers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['keitaro_id']),
            models.Index(fields=['user', 'state']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f'{self.name} (ID: {self.keitaro_id})'


class FlowOffer(models.Model):
    """Связь потока и оффера (распределение офферов в потоке)"""
    
    STATE_CHOICES = [
        ('active', 'Активен'),
        ('disabled', 'Отключен'),
    ]
    
    flow = models.ForeignKey(
        Flow,
        on_delete=models.CASCADE,
        related_name='flow_offers',
        verbose_name='Поток'
    )
    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name='flow_offers',
        verbose_name='Оффер'
    )
    share = models.IntegerField(
        default=0,
        verbose_name='Доля (%)',
        help_text='Процент трафика (0-100)'
    )
    is_pinned = models.BooleanField(
        default=False,
        verbose_name='Зафиксирован',
        help_text='Зафиксированный share не пересчитывается автоматически'
    )
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='active',
        verbose_name='Состояние'
    )
    keitaro_offer_stream_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID связи в Keitaro'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Оффер в потоке'
        verbose_name_plural = 'Офферы в потоках'
        db_table = 'flow_offers'
        unique_together = [['flow', 'offer']]
        ordering = ['flow', '-share']
        indexes = [
            models.Index(fields=['flow', 'state']),
            models.Index(fields=['keitaro_offer_stream_id']),
        ]
    
    def __str__(self):
        return f'{self.offer.name} в {self.flow.name} ({self.share}%)'
