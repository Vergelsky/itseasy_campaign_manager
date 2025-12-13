from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.conf import settings
from .forms import LoginForm
from .models import User
from campaigns.services import KeitaroClient, KeitaroAPIException


class LoginView(View):
    """Страница входа по API ключу"""
    
    def get(self, request):
        """Отображение формы входа"""
        # Если уже авторизован, редирект на главную
        if request.session.get('user_id'):
            return redirect('campaigns:campaign_list')
        
        form = LoginForm()
        keitaro_url = settings.KEITARO_URL
        
        return render(request, 'users/login.html', {
            'form': form,
            'keitaro_url': keitaro_url,
        })
    
    def post(self, request):
        """Обработка входа"""
        form = LoginForm(request.POST)
        
        if not form.is_valid():
            return render(request, 'users/login.html', {'form': form})
        
        api_key = form.cleaned_data['api_key']
        
        # Валидация API ключа через Keitaro
        try:
            client = KeitaroClient(settings.KEITARO_URL, api_key)
            if not client.validate_api_key():
                messages.error(request, 'Неверный API ключ')
                return render(request, 'users/login.html', {'form': form})
        except KeitaroAPIException as e:
            messages.error(request, f'Ошибка подключения к Keitaro: {str(e)}')
            return render(request, 'users/login.html', {'form': form})
        
        # Создание или получение пользователя
        user, created = User.objects.get_or_create(
            api_key=api_key,
            defaults={
                'is_active': True,
            }
        )
        
        # Сохранение в session
        request.session['user_id'] = user.id
        
        # Редирект на последнюю страницу или главную
        next_url = user.last_page if user.last_page else 'campaigns:campaign_list'
        
        if created:
            messages.success(request, 'Добро пожаловать! Вы успешно вошли в систему.')
        else:
            messages.success(request, 'С возвращением!')
        
        return redirect(next_url)


class LogoutView(View):
    """Выход из системы"""
    
    def get(self, request):
        """Выход и очистка session"""
        request.session.flush()
        messages.success(request, 'Вы успешно вышли из системы')
        return redirect('users:login')
