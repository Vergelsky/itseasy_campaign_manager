from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    """Менеджер для кастомной модели User"""
    
    def create_user(self, api_key, password=None, **extra_fields):
        """Создание обычного пользователя"""
        if not api_key:
            raise ValueError('API ключ обязателен')
        
        user = self.model(api_key=api_key, **extra_fields)
        # ВАЖНО: устанавливаем пароль через set_password для правильного хэширования
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, api_key, password=None, **extra_fields):
        """Создание суперпользователя"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        # ВАЖНО: передаем password в create_user
        return self.create_user(api_key, password=password, **extra_fields)


class User(AbstractUser, PermissionsMixin):
    """
    Кастомная модель пользователя.
    Аутентификация через API ключ Keitaro (без пароля).
    """
    # ПЕРЕОПРЕДЕЛЯЕМ username чтобы убрать уникальность и сделать необязательным
    username = models.CharField(
        max_length=150,
        unique=False,  # Убираем уникальность
        blank=True,    # Разрешаем пустое значение
        null=True,     # Разрешаем NULL в базе
        verbose_name='Имя пользователя',
        help_text='Не используется для входа'
    )
    
    api_key = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='API ключ Keitaro'
    )
    password = models.CharField(max_length=128, blank=True, null=True, verbose_name='Пароль')
    last_page = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Последняя посещённая страница'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    objects = UserManager()
    
    USERNAME_FIELD = 'api_key'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        db_table = 'users'
    
    def __str__(self):
        return f'User {self.id} ({self.api_key[:10]}...)' if self.api_key else f'User {self.id}'
    
    def get_full_name(self):
        return f'User {self.id}'
    
    def get_short_name(self):
        return f'User {self.id}'
