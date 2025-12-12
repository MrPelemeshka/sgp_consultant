from django.contrib import admin
from .models import (
    MineralType, Stage, Question, 
    Work, UserGanttChart
)
from django import forms

class WorkAdminForm(forms.ModelForm):
    """
    Форма для администрирования работ с удобным редактированием
    """
    class Meta:
        model = Work
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'executor': forms.Textarea(attrs={'rows': 2}),
        }

@admin.register(MineralType)
class MineralTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')
    prepopulated_fields = {'code': ('name',)}

@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ('name', 'mineral_type', 'order', 'duration_months', 'start_month')
    list_filter = ('mineral_type',)
    search_fields = ('name', 'description')
    list_editable = ('order', 'duration_months', 'start_month')
    filter_horizontal = ('depends_on',)
    fieldsets = (
        ('Основное', {
            'fields': ('mineral_type', 'name', 'code', 'order', 'description')
        }),
        ('Время', {
            'fields': ('duration_months', 'start_month')
        }),
        ('Отображение', {
            'fields': ('color',)
        }),
        ('Зависимости', {
            'fields': ('depends_on',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'code')
    search_fields = ('text', 'code')
    filter_horizontal = ('mineral_types', 'target_stages')

@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    form = WorkAdminForm
    list_display = ('number', 'title', 'stage', 'duration_months', 'start_month', 'order')
    list_filter = ('stage__mineral_type', 'stage')
    search_fields = ('title', 'description', 'number')
    list_editable = ('order', 'duration_months', 'start_month')
    fieldsets = (
        ('Основное', {
            'fields': ('stage', 'number', 'title')
        }),
        ('Детали', {
            'fields': ('description', 'executor')
        }),
        ('Время', {
            'fields': ('duration_months', 'start_month')
        }),
        ('Порядок', {
            'fields': ('order',)
        }),
    )

@admin.register(UserGanttChart)
class UserGanttChartAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'mineral_type', 'start_stage', 'created_at')
    list_filter = ('mineral_type', 'created_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at', 'updated_at')