from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.conf import settings
from .forms import LoginForm
from .models import User
from campaigns.services import KeitaroClient
from config.exceptions import KeitaroAPIException, KeitaroAuthException, KeitaroConnectionException


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
        
        # Проверяем, существует ли пользователь с таким API ключом
        try:
            existing_user = User.objects.get(api_key=api_key)
            # Если пользователь уже существует, пропускаем валидацию
            # (предполагаем, что ключ был валидным при первом входе)
            user = existing_user
            created = False
        except User.DoesNotExist:
            # Пользователь не существует - валидируем API ключ через Keitaro
            try:
                client = KeitaroClient(settings.KEITARO_URL, api_key)
                if not client.validate_api_key():
                    messages.error(request, 'Неверный API ключ')
                    return render(request, 'users/login.html', {'form': form})
            except KeitaroAuthException:
                # Неверный API ключ
                messages.error(request, 'Неверный API ключ')
                return render(request, 'users/login.html', {'form': form})
            except KeitaroConnectionException as e:
                # Проблемы с подключением к Keitaro
                messages.error(request, f'Не удалось подключиться к Keitaro: {str(e)}')
                return render(request, 'users/login.html', {'form': form})
            except KeitaroAPIException as e:
                # Другие ошибки API
                messages.error(request, f'Ошибка при подключении к Keitaro: {str(e)}')
                return render(request, 'users/login.html', {'form': form})
            
            # Создаем нового пользователя
            user = User.objects.create(
                api_key=api_key,
                is_active=True,
            )
            created = True
        
        # Проверяем, что пользователь активен
        if not user.is_active:
            messages.error(request, 'Ваш аккаунт деактивирован')
            return render(request, 'users/login.html', {'form': form})
        
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
