from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админ-панель для модели User"""
    
    list_display = ('id', 'api_key_short', 'is_active', 'is_staff', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('api_key',)
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('api_key',)}),
        ('Персональная информация', {'fields': ('last_page',)}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('api_key', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    def api_key_short(self, obj):
        """Отображение укороченного API ключа"""
        if obj.api_key:
            return f'{obj.api_key[:20]}...' if len(obj.api_key) > 20 else obj.api_key
        return '-'
    api_key_short.short_description = 'API ключ'
