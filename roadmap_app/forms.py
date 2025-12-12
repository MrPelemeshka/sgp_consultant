from django import forms
from .models import UserGanttChart, MineralType, Stage, Question

class GanttChartCreationForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        label='Название проекта',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Например: Разработка угольного месторождения Сибирь-1'
        })
    )
    
    # Скрытые поля для хранения выбранных ID
    mineral_type_id = forms.IntegerField(widget=forms.HiddenInput(), required=True)
    start_stage_id = forms.IntegerField(widget=forms.HiddenInput(), required=True)
    question_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    
    def clean_mineral_type_id(self):
        mineral_id = self.cleaned_data['mineral_type_id']
        try:
            return MineralType.objects.get(id=mineral_id)
        except MineralType.DoesNotExist:
            raise forms.ValidationError('Выберите корректный тип полезного ископаемого')
    
    def clean_start_stage_id(self):
        stage_id = self.cleaned_data['start_stage_id']
        if not stage_id:
            raise forms.ValidationError('Выберите начальный этап')
        
        try:
            stage = Stage.objects.get(id=stage_id)
            return stage
        except Stage.DoesNotExist:
            raise forms.ValidationError('Выберите корректный начальный этап')
    
    def clean_question_id(self):
        question_id = self.cleaned_data.get('question_id')
        if question_id:
            try:
                question = Question.objects.get(id=question_id)
                return question
            except Question.DoesNotExist:
                raise forms.ValidationError('Выберите корректный вопрос')
        return None
    
    def save(self, user):
        mineral_type = self.cleaned_data['mineral_type_id']
        start_stage = self.cleaned_data['start_stage_id']
        question = self.cleaned_data['question_id']
    
        chart = UserGanttChart.objects.create(
            user=user,
            title=self.cleaned_data['title'],
            mineral_type=mineral_type,
            start_stage=start_stage,
            question=question,
            chart_data={} 
        )
        
        return chart