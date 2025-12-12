# roadmap_app/admin_forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
import pandas as pd
from io import StringIO
from .models import (
    MineralType, Stage, Work, Question, FAQ,
    DataImportTemplate, DataImportLog
)

class MineralTypeForm(forms.ModelForm):
    class Meta:
        model = MineralType
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Уголь'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: COAL'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание типа полезного ископаемого'
            }),
        }

class StageForm(forms.ModelForm):
    class Meta:
        model = Stage
        fields = ['mineral_type', 'name', 'code', 'order', 'description', 
                 'duration_months', 'start_month', 'color', 'depends_on']
        widgets = {
            'mineral_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Лицензирование'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: LICENSING'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'start_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'depends_on': forms.SelectMultiple(attrs={
                'class': 'form-control select2',
                'style': 'width: 100%;'
            }),
        }

class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        fields = ['stage', 'number', 'title', 'description', 'executor',
                 'duration_months', 'start_month', 'order']
        widgets = {
            'stage': forms.Select(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: 1.1.1'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название работы'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'executor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Геологическая служба'
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'start_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'code', 'description', 'mineral_types', 'target_stages']
        widgets = {
            'text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Текст вопроса'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Код вопроса'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'mineral_types': forms.SelectMultiple(attrs={
                'class': 'form-control select2'
            }),
            'target_stages': forms.SelectMultiple(attrs={
                'class': 'form-control select2'
            }),
        }

class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['question', 'answer', 'keywords', 'order', 'is_active']
        widgets = {
            'question': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Вопрос'
            }),
            'answer': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ответ'
            }),
            'keywords': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Ключевые слова через запятую'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class DataImportForm(forms.Form):
    MODEL_CHOICES = [
        ('mineral_type', 'Типы полезных ископаемых'),
        ('stage', 'Этапы'),
        ('work', 'Работы'),
        ('question', 'Вопросы'),
        ('faq', 'FAQ'),
    ]
    
    model_type = forms.ChoiceField(
        choices=MODEL_CHOICES,
        label='Тип данных',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    import_file = forms.FileField(
        label='Файл для импорта',
        help_text='Поддерживаемые форматы: JSON, CSV, Excel',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    import_mode = forms.ChoiceField(
        choices=[
            ('create', 'Создать новые записи'),
            ('update', 'Обновить существующие'),
            ('upsert', 'Создать или обновить'),
        ],
        initial='upsert',
        label='Режим импорта',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    validate_data = forms.BooleanField(
        required=False,
        initial=True,
        label='Валидировать данные',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_import_file(self):
        file = self.cleaned_data['import_file']
        ext = file.name.split('.')[-1].lower()
        if ext not in ['json', 'csv', 'xlsx', 'xls']:
            raise ValidationError('Поддерживаются только файлы JSON, CSV и Excel')
        return file

class BulkEditForm(forms.Form):
    """
    Форма для массового редактирования
    """
    model_type = forms.ChoiceField(
        choices=[
            ('mineral_type', 'Типы полезных ископаемых'),
            ('stage', 'Этапы'),
            ('work', 'Работы'),
            ('question', 'Вопросы'),
        ],
        label='Тип данных',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    field_to_edit = forms.CharField(
        label='Поле для изменения',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: description'
        })
    )
    
    new_value = forms.CharField(
        label='Новое значение',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Введите новое значение'
        })
    )
    
    def clean_ids(self):
        ids = self.cleaned_data['ids']
        try:
            id_list = [int(id.strip()) for id in ids.split(',') if id.strip()]
            if not id_list:
                raise ValidationError('Не выбраны записи для редактирования')
            return id_list
        except ValueError:
            raise ValidationError('Некорректный формат ID')

class ExportDataForm(forms.Form):
    model_type = forms.ChoiceField(
        choices=[
            ('mineral_type', 'Типы полезных ископаемых'),
            ('stage', 'Этапы'),
            ('work', 'Работы'),
            ('question', 'Вопросы'),
            ('faq', 'FAQ'),
        ],
        label='Тип данных для экспорта',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    format = forms.ChoiceField(
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('excel', 'Excel'),
        ],
        initial='json',
        label='Формат экспорта',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_all = forms.BooleanField(
        required=False,
        initial=True,
        label='Экспортировать все поля',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )