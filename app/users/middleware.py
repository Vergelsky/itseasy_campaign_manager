from django.shortcuts import redirect
from django.urls import reverse
from .models import User


class AuthMiddleware:
    """
    Middleware для проверки аутентификации пользователя
    Проверяет наличие user_id в session и редиректит на login если не авторизован
    """
    
    # URL которые не требуют аутентификации
    ALLOWED_PATHS = [
        '/users/login/',
        '/admin/',  # Django admin имеет свою аутентификацию
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверяем, нужна ли аутентификация для этого URL
        path = request.path
        
        # Пропускаем allowed paths и static/media
        if any(path.startswith(allowed) for allowed in self.ALLOWED_PATHS):
            return self.get_response(request)
        
        if path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)
        
        # Проверяем наличие user_id в session
        user_id = request.session.get('user_id')
        
        if not user_id:
            # Не авторизован - редирект на login
            return redirect('users:login')
        
        # Проверяем что пользователь существует и активен
        try:
            user = User.objects.get(id=user_id, is_active=True)
            request.user = user
            
            # Сохраняем текущую страницу как last_page (кроме AJAX и служебных страниц)
            excluded_paths = ['/users/login/', '/users/logout/']
            if (not request.headers.get('X-Requested-With') == 'XMLHttpRequest' and
                not any(path.startswith(excluded_path) for excluded_path in excluded_paths)):
                if user.last_page != path:
                    user.last_page = path
                    user.save(update_fields=['last_page'])
        
        except User.DoesNotExist:
            # Пользователь не найден - очищаем session
            request.session.flush()
            return redirect('users:login')
        
        response = self.get_response(request)
        return response

