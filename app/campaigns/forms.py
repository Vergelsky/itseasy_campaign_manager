from django import forms
from .models import Offer


class CreateCampaignForm(forms.Form):
    """Форма для создания рекламной кампании"""
    
    name = forms.CharField(
        label='Название кампании',
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Введите название кампании'
        })
    )
    
    geo_codes = forms.CharField(
        label='Гео-коды стран',
        required=True,
        help_text='Введите коды стран через запятую (например: US,GB,DE)',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'US,GB,DE,FR'
        })
    )
    
    offer_id = forms.IntegerField(
        label='Оффер',
        required=True,
        widget=forms.HiddenInput()
    )
    
    offer_name = forms.CharField(
        label='Оффер',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 offer-autocomplete',
            'placeholder': 'Начните вводить название оффера...',
            'autocomplete': 'off'
        })
    )

