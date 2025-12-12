import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from roadmap_app.models import MineralType, Stage, Question, Work, FAQ

class Command(BaseCommand):
    help = 'Загрузка начальных данных из JSON файлов'
    
    def handle(self, *args, **kwargs):
        base_dir = settings.BASE_DIR
        data_dir = os.path.join(base_dir, 'data')
        
        # Загружаем типы полезных ископаемых
        self.stdout.write('📥 Загрузка типов полезных ископаемых...')
        mineral_types_path = os.path.join(data_dir, 'mineral_types.json')
        if os.path.exists(mineral_types_path):
            with open(mineral_types_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    mineral, created = MineralType.objects.get_or_create(
                        id=item['pk'],
                        defaults={
                            'name': item['fields']['name'],
                            'code': item['fields']['code'],
                            'description': item['fields']['description']
                        }
                    )
                    if created:
                        self.stdout.write(f'  ✅ Создан: {mineral.name}')
                    else:
                        self.stdout.write(f'  ⚡ Обновлен: {mineral.name}')
        
        # Загружаем этапы
        self.stdout.write('📥 Загрузка этапов...')
        stages_path = os.path.join(data_dir, 'stages.json')
        if os.path.exists(stages_path):
            with open(stages_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    try:
                        mineral_type = MineralType.objects.get(id=item['fields']['mineral_type'])
                        
                        stage, created = Stage.objects.get_or_create(
                            id=item['pk'],
                            defaults={
                                'mineral_type': mineral_type,
                                'name': item['fields']['name'],
                                'code': item['fields']['code'],
                                'order': item['fields']['order'],
                                'description': item['fields']['description'],
                                'duration_months': item['fields']['duration_months'],
                                'start_month': item['fields']['start_month'],
                                'color': item['fields']['color']
                            }
                        )
                        
                        # Добавляем зависимости
                        depends_on_ids = item['fields'].get('depends_on', [])
                        for dep_id in depends_on_ids:
                            try:
                                dep_stage = Stage.objects.get(id=dep_id)
                                stage.depends_on.add(dep_stage)
                            except Stage.DoesNotExist:
                                pass
                        
                        if created:
                            self.stdout.write(f'  ✅ Создан этап: {stage.name}')
                        else:
                            self.stdout.write(f'  ⚡ Обновлен этап: {stage.name}')
                            
                    except MineralType.DoesNotExist:
                        self.stdout.write(f'  ❌ Ошибка: минеральный тип не найден для этапа {item["pk"]}')
        
        # Загружаем вопросы
        self.stdout.write('📥 Загрузка вопросов...')
        questions_path = os.path.join(data_dir, 'questions.json')
        if os.path.exists(questions_path):
            with open(questions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    question, created = Question.objects.get_or_create(
                        id=item['pk'],
                        defaults={
                            'text': item['fields']['text'],
                            'code': item['fields']['code'],
                            'description': item['fields']['description']
                        }
                    )
                    
                    # Добавляем связи с типами ПИ
                    mineral_ids = item['fields'].get('mineral_types', [])
                    for mineral_id in mineral_ids:
                        try:
                            mineral = MineralType.objects.get(id=mineral_id)
                            question.mineral_types.add(mineral)
                        except MineralType.DoesNotExist:
                            pass
                    
                    # Добавляем целевые этапы
                    target_stage_ids = item['fields'].get('target_stages', [])
                    for stage_id in target_stage_ids:
                        try:
                            stage = Stage.objects.get(id=stage_id)
                            question.target_stages.add(stage)
                        except Stage.DoesNotExist:
                            pass
                    
                    if created:
                        self.stdout.write(f'  ✅ Создан вопрос: {question.text[:50]}...')
                    else:
                        self.stdout.write(f'  ⚡ Обновлен вопрос: {question.text[:50]}...')
        
        # Загружаем работы
        self.stdout.write('📥 Загрузка работ...')
        works_path = os.path.join(data_dir, 'works.json')
        if os.path.exists(works_path):
            with open(works_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    try:
                        stage = Stage.objects.get(id=item['fields']['stage'])
                        
                        work, created = Work.objects.get_or_create(
                            id=item['pk'],
                            defaults={
                                'stage': stage,
                                'number': item['fields']['number'],
                                'title': item['fields']['title'],
                                'description': item['fields']['description'],
                                'executor': item['fields']['executor'],
                                'duration_months': item['fields']['duration_months'],
                                'start_month': item['fields']['start_month'],
                                'order': item['fields']['order']
                            }
                        )
                        
                        if created:
                            self.stdout.write(f'  ✅ Создана работа: {work.number} - {work.title[:30]}...')
                        else:
                            self.stdout.write(f'  ⚡ Обновлена работа: {work.number} - {work.title[:30]}...')
                            
                    except Stage.DoesNotExist:
                        self.stdout.write(f'  ❌ Ошибка: этап не найден для работы {item["pk"]}')
        
        # Загружаем FAQ
        self.stdout.write('📥 Загрузка FAQ...')
        faq_path = os.path.join(data_dir, 'faq.json')
        if os.path.exists(faq_path):
            with open(faq_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    faq, created = FAQ.objects.get_or_create(
                        id=item['pk'],
                        defaults={
                            'question': item['fields']['question'],
                            'answer': item['fields']['answer'],
                            'keywords': item['fields']['keywords'],
                            'order': item['fields']['order'],
                            'is_active': item['fields']['is_active']
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'  ✅ Создан FAQ: {faq.question[:50]}...')
                    else:
                        self.stdout.write(f'  ⚡ Обновлен FAQ: {faq.question[:50]}...')
        
        self.stdout.write(self.style.SUCCESS('✅ Все данные успешно загружены!'))
        self.stdout.write(f'📊 Статистика:')
        self.stdout.write(f'  Типы ПИ: {MineralType.objects.count()}')
        self.stdout.write(f'  Этапы: {Stage.objects.count()}')
        self.stdout.write(f'  Вопросы: {Question.objects.count()}')
        self.stdout.write(f'  Работы: {Work.objects.count()}')
        self.stdout.write(f'  FAQ: {FAQ.objects.count()}')