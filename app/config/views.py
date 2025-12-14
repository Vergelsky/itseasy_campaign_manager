"""
Обработчики ошибок для кастомных страниц
"""
from django.shortcuts import render


def handler404(request, exception):
    """Обработчик 404 ошибки"""
    return render(request, '404.html', status=404)


def handler500(request):
    """Обработчик 500 ошибки"""
    return render(request, '500.html', status=500)


def handler403(request, exception):
    """Обработчик 403 ошибки"""
    return render(request, '403.html', status=403)

