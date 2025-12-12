from rest_framework import serializers
from .models import MineralType, ProjectStage, Question, StageWork, UserGanttChart

class MineralTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MineralType
        fields = ['id', 'name', 'code', 'description']

class ProjectStageSerializer(serializers.ModelSerializer):
    mineral_types = MineralTypeSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProjectStage
        fields = ['id', 'name', 'code', 'order', 'description', 'mineral_types']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'text', 'code', 'description']

class StageWorkSerializer(serializers.ModelSerializer):
    project_stage = ProjectStageSerializer(read_only=True)
    mineral_type = MineralTypeSerializer(read_only=True)
    related_questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = StageWork
        fields = '__all__'

class UserGanttChartSerializer(serializers.ModelSerializer):
    mineral_type = MineralTypeSerializer(read_only=True)
    project_stage = ProjectStageSerializer(read_only=True)
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = UserGanttChart
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']