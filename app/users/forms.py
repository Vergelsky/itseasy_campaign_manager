from django import forms
from .models import User


class LoginForm(forms.Form):
    """Форма входа по API ключу"""
    
    api_key = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Введите ваш API ключ Keitaro',
            'autocomplete': 'off',
        }),
        label='API ключ'
    )

