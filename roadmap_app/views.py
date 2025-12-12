from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.generic import TemplateView
from django.db.models import Q
from .models import FAQ, MineralType, Stage, Question, Work, UserGanttChart
from .forms import GanttChartCreationForm
from .models import DataImportLog
from .admin_forms import ( 
    MineralTypeForm, StageForm, WorkForm, 
    QuestionForm, FAQForm, DataImportForm,
    ExportDataForm, BulkEditForm
)
import json
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
from io import BytesIO, StringIO
import tempfile
import os
from django.contrib.auth.decorators import user_passes_test


def check_moderator(user):
    """Проверка, является ли пользователь модератором"""
    # Используем метод из вашей модели CustomUser
    if hasattr(user, 'is_moderator'):
        return user.is_moderator()
    # Запасной вариант: суперпользователь всегда модератор
    return user.is_superuser

def moderator_required(function=None):
    """
    Декоратор для проверки прав модератора
    """
    actual_decorator = user_passes_test(
        check_moderator,
        login_url='/dashboard/',
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

class HomeView(TemplateView):
    """
    Главная страница
    """
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faqs'] = FAQ.objects.filter(is_active=True).order_by('order')[:5]
        return context

@login_required
def dashboard(request):
    """
    Личный кабинет пользователя
    """
    user_charts = UserGanttChart.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'roadmap_app/dashboard.html', {
        'charts': user_charts
    })

def prepare_chart_data(mineral_type, start_stage, question):
    """
    Подготавливает данные для диаграммы Ганта с правильными зависимостями
    """
    # Получаем все этапы для данного типа ПИ, упорядоченные
    all_stages = Stage.objects.filter(
        mineral_type=mineral_type
    ).prefetch_related('depends_on', 'works').order_by('order')
    
    # Создаем словарь для быстрого доступа
    stage_dict = {stage.id: stage for stage in all_stages}
    
    # Определяем, до каких этапов нужно идти
    target_stage_ids = set()
    
    if question:
        # Берем целевые этапы из вопроса
        target_stage_ids = set(question.target_stages.filter(
            mineral_type=mineral_type
        ).values_list('id', flat=True))
    else:
        # Если вопроса нет, идем до конца всех этапов
        start_order = start_stage.order
        target_stage_ids = set(
            stage.id for stage in all_stages 
            if stage.order >= start_order
        )
    
    # Функция для топологической сортировки этапов с учетом зависимостей
    def topological_sort(stage_ids):
        visited = set()
        stack = []
        
        def dfs(stage_id):
            if stage_id in visited:
                return
            visited.add(stage_id)
            
            stage = stage_dict.get(stage_id)
            if stage:
                # Сначала посещаем зависимости
                for dep in stage.depends_on.all():
                    if dep.mineral_type == mineral_type:
                        dfs(dep.id)
                
                # Затем добавляем текущий этап
                if stage_id in stage_ids:
                    stack.append(stage_id)
        
        for stage_id in sorted(stage_ids, key=lambda x: stage_dict[x].order):
            dfs(stage_id)
        
        return stack
    
    # Получаем этапы в правильном порядке с учетом зависимостей
    included_stage_ids = topological_sort(target_stage_ids)
    
    # Добавляем начальный этап, если его еще нет
    if start_stage.id not in included_stage_ids:
        # Находим его место с учетом зависимостей
        included_stage_ids.insert(0, start_stage.id)
    
    # Фильтруем этапы, которые идут после начального
    included_stages = [
        stage_dict[stage_id] for stage_id in included_stage_ids
        if stage_dict[stage_id].order >= start_stage.order
    ]
    
    # Сортируем по порядку
    included_stages.sort(key=lambda x: x.order)
    
    # Подготавливаем данные для каждого этапа
    stages_data = []
    current_global_time = 0
    
    for stage in included_stages:
        # Рассчитываем начало этапа с учетом максимального времени окончания зависимостей
        stage_start = current_global_time
        
        # Если есть зависимости, находим максимальное время их окончания
        if stage.depends_on.exists():
            max_dep_end = 0
            for dep in stage.depends_on.all():
                if dep.id in [s.id for s in included_stages]:
                    # Находим предыдущий этап в списке
                    for prev_stage in stages_data:
                        if prev_stage['id'] == dep.id:
                            dep_end = prev_stage['start'] + prev_stage['duration']
                            if dep_end > max_dep_end:
                                max_dep_end = dep_end
            
            if max_dep_end > stage_start:
                stage_start = max_dep_end
        
        # Получаем работы для этого этапа
        works = stage.works.all().order_by('order')
        works_data = []
        
        for work in works:
            works_data.append({
                'id': work.id,
                'number': work.number,
                'title': work.title,
                'description': work.description,
                'executor': work.executor,
                'duration_months': work.duration_months, 
                'start_month': work.start_month,  # Используем start_month вместо start_in_stage
                'order': work.order
            })
        
        # Рассчитываем длительность этапа
        stage_duration = stage.duration_months
        if works_data:
            # ИСПРАВЛЕНИЕ: Используем правильные ключи
            max_work_end = 0
            for w in works_data:
                work_start = w.get('start_month', 0)  # Используем start_month
                work_duration = w.get('duration_months', 1)
                work_end = work_start + work_duration
                if work_end > max_work_end:
                    max_work_end = work_end
            
            if max_work_end > stage_duration:
                stage_duration = max_work_end
        
        # Добавляем зависимости для отрисовки стрелок
        dependencies = []
        for dep in stage.depends_on.all():
            if dep.mineral_type == mineral_type:
                dependencies.append(dep.id)
        
        stage_data = {
            'id': stage.id,
            'name': stage.name,
            'order': stage.order,
            'description': stage.description,
            'color': stage.color,
            'start': stage_start,
            'duration': stage_duration,
            'works': works_data,
            'dependencies': dependencies,
            'total_duration': stage_duration
        }
        
        stages_data.append(stage_data)
        current_global_time = stage_start + stage_duration
    
    # Обновляем works_data с глобальным временем
    for stage_data in stages_data:
        for work in stage_data['works']:
            work['start_global'] = stage_data['start'] + work.get('start_month', 0)
            # Добавляем совместимость со старым ключом
            work['start_in_stage'] = work.get('start_month', 0)
    
    # Общая длительность
    total_duration = current_global_time
    
    return {
        'mineral_type': {
            'id': mineral_type.id,
            'name': mineral_type.name,
            'code': mineral_type.code
        },
        'start_stage': {
            'id': start_stage.id,
            'name': start_stage.name
        },
        'question': {
            'id': question.id,
            'text': question.text,
            'code': question.code
        } if question else None,
        'stages': stages_data,
        'total_duration': total_duration
    }

@login_required
def create_gantt(request):
    """
    Создание новой диаграммы Ганта
    """
    if request.method == 'POST':
        form = GanttChartCreationForm(request.POST)
        
        if form.is_valid():
            try:
                # Создаем диаграмму
                chart = form.save(request.user)
                
                # ТЕПЕРЬ готовим данные и сохраняем их
                mineral_type = form.cleaned_data['mineral_type_id']
                start_stage = form.cleaned_data['start_stage_id']
                question = form.cleaned_data['question_id']
                
                # Подготавливаем данные для диаграммы
                chart_data = prepare_chart_data(mineral_type, start_stage, question)
                
                # Сохраняем данные в диаграмме
                chart.chart_data = chart_data
                chart.save()
                
                messages.success(request, '✅ Диаграмма успешно создана!')
                return redirect('view_gantt', chart_id=chart.id)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'❌ Ошибка при создании диаграммы: {str(e)}')
        else:
            # Показываем все ошибки формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = GanttChartCreationForm()
    
    # Получаем типы ПИ для отображения
    mineral_types = MineralType.objects.all()
    
    return render(request, 'roadmap_app/create_gantt.html', {
        'form': form,
        'mineral_types': mineral_types
    })

@login_required
def view_gantt(request, chart_id):
    """
    Просмотр конкретной диаграммы Ганта
    """
    chart = get_object_or_404(UserGanttChart, id=chart_id, user=request.user)
    
    # Отладка - посмотрим, что хранится в chart_data
    print("Chart data:", chart.chart_data)
    
    try:
        # Проверяем структуру данных
        if not chart.chart_data or 'stages' not in chart.chart_data:
            print("Некорректные данные диаграммы")
            # Создаем минимальные данные
            chart_data = {
                'mineral_type': {'name': chart.mineral_type.name if chart.mineral_type else 'Не указан'},
                'start_stage': {'name': chart.start_stage.name if chart.start_stage else 'Не указана'},
                'stages': [],
                'total_duration': 0
            }
        else:
            chart_data = chart.chart_data
            
        # Преобразуем данные в JSON
        chart_data_json = json.dumps(chart_data, ensure_ascii=False, default=str)
        
    except Exception as e:
        print(f"Ошибка при обработке данных: {e}")
        # Создаем минимальные данные при ошибке
        chart_data_json = json.dumps({
            'mineral_type': {'name': 'Ошибка данных'},
            'start_stage': {'name': 'Ошибка данных'},
            'stages': [],
            'total_duration': 0
        }, ensure_ascii=False)
    
    return render(request, 'roadmap_app/gantt_chart.html', {
        'chart': chart,
        'chart_data_json': chart_data_json
    })

@login_required
def get_filtered_stages(request):
    """AJAX запрос для получения этапов по выбранному типу ПИ"""
    mineral_type_id = request.GET.get('mineral_type')
    
    if not mineral_type_id:
        return JsonResponse({'stages': []})
    
    try:
        mineral_type = MineralType.objects.get(id=mineral_type_id)
        stages = Stage.objects.filter(
            mineral_type=mineral_type
        ).order_by('order').values('id', 'name', 'order', 'description')
        
        return JsonResponse({
            'stages': list(stages),
            'success': True
        })
        
    except MineralType.DoesNotExist:
        return JsonResponse({'stages': [], 'success': False})

@login_required
def get_filtered_questions(request):
    """AJAX запрос для получения вопросов по выбранному типу ПИ"""
    mineral_type_id = request.GET.get('mineral_type')
    
    if not mineral_type_id:
        return JsonResponse({'questions': []})
    
    try:
        mineral_type = MineralType.objects.get(id=mineral_type_id)
        questions = Question.objects.filter(
            mineral_types=mineral_type
        ).values('id', 'text', 'code', 'description')
        
        return JsonResponse({
            'questions': list(questions),
            'success': True
        })
        
    except MineralType.DoesNotExist:
        return JsonResponse({'questions': [], 'success': False})

@login_required
def get_works_for_selection(request):
    """
    AJAX запрос для получения работ по выбранным параметрам
    """
    mineral_type_id = request.GET.get('mineral_type')
    stage_id = request.GET.get('stage')
    question_id = request.GET.get('question')
    
    if not mineral_type_id or not stage_id:
        return JsonResponse({'works': []})
    
    try:
        # Используем реальные модели
        works = Work.objects.filter(stage_id=stage_id)
        
        works_data = []
        for work in works.order_by('order'):
            works_data.append({
                'id': work.id,
                'number': work.number,
                'title': work.title,
                'description': work.description,
                'executor': work.executor,
                'duration_months': work.duration_months, 
                'start_month': work.start_month, 
                'order': work.order
            })
        
        return JsonResponse({
            'works': works_data,
            'success': True
        })
        
    except Exception:
        return JsonResponse({'works': [], 'success': False})

@login_required
def delete_gantt(request, chart_id):
    """
    Удаление диаграммы Ганта
    """
    chart = get_object_or_404(UserGanttChart, id=chart_id, user=request.user)
    
    if request.method == 'POST':
        chart.delete()
        messages.success(request, 'Диаграмма успешно удалена')
        return redirect('dashboard')
    
    return render(request, 'roadmap_app/confirm_delete.html', {'chart': chart})

def faq_search(request):
    """
    Поиск по FAQ
    """
    query = request.GET.get('q', '')
    faqs = FAQ.objects.filter(is_active=True)
    
    if query:
        # Ищем по ключевым словам и тексту вопроса
        faqs = faqs.filter(
            Q(question__icontains=query) |
            Q(answer__icontains=query) |
            Q(keywords__icontains=query)
        )
    
    return render(request, 'roadmap_app/faq_search.html', {
        'faqs': faqs,
        'query': query
    })

@login_required
@moderator_required
def admin_dashboard(request):
    """
    Административная панель для управления данными
    """
    
    # Статистика
    stats = {
        'mineral_types': MineralType.objects.count(),
        'stages': Stage.objects.count(),
        'works': Work.objects.count(),
        'questions': Question.objects.count(),
        'faqs': FAQ.objects.count(),
        'recent_imports': DataImportLog.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5] if hasattr(DataImportLog, 'user') else []
    }
    
    return render(request, 'admin/admin_dashboard.html', {
        'stats': stats
    })

@login_required
@moderator_required
def data_management(request, model_type):
    """
    Управление данными конкретного типа
    """
    
    # Определяем модель по типу
    model_map = {
        'mineral_type': MineralType,
        'stage': Stage,
        'work': Work,
        'question': Question,
        'faq': FAQ,
    }
    
    if model_type not in model_map:
        return redirect('admin_dashboard')
    
    model = model_map[model_type]
    items = model.objects.all()
    
    # Определяем форму для добавления
    form_map = {
        'mineral_type': MineralTypeForm,
        'stage': StageForm,
        'work': WorkForm,
        'question': QuestionForm,
        'faq': FAQForm,
    }
    
    form_class = form_map.get(model_type)
    
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            instance = form.save()
            messages.success(request, f'✅ Запись успешно добавлена')
            return redirect('data_management', model_type=model_type)
    else:
        form = form_class()
    
    return render(request, 'admin/data_management.html', {
        'model_type': model_type,
        'model_name': model._meta.verbose_name_plural,
        'items': items,
        'form': form,
        'total_count': items.count()
    })

@login_required
@moderator_required
def edit_data(request, model_type, item_id):
    """
    Редактирование записи
    """
    
    model_map = {
        'mineral_type': MineralType,
        'stage': Stage,
        'work': Work,
        'question': Question,
        'faq': FAQ,
    }
    
    if model_type not in model_map:
        return redirect('admin_dashboard')
    
    model = model_map[model_type]
    item = get_object_or_404(model, id=item_id)
    
    form_map = {
        'mineral_type': MineralTypeForm,
        'stage': StageForm,
        'work': WorkForm,
        'question': QuestionForm,
        'faq': FAQForm,
    }
    
    form_class = form_map.get(model_type)
    
    if request.method == 'POST':
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Запись успешно обновлена')
            return redirect('data_management', model_type=model_type)
    else:
        form = form_class(instance=item)
    
    # Добавляем display_name для корректного отображения в шаблоне
    context = {
        'model_type': model_type,
        'model_name': model._meta.verbose_name,
        'item': item,
        'form': form
    }
    
    return render(request, 'admin/edit_data.html', context)

@login_required
@moderator_required
def delete_data(request, model_type, item_id):
    """
    Удаление записи
    """
    
    model_map = {
        'mineral_type': MineralType,
        'stage': Stage,
        'work': Work,
        'question': Question,
        'faq': FAQ,
    }
    
    if model_type not in model_map:
        return redirect('admin_dashboard')
    
    model = model_map[model_type]
    item = get_object_or_404(model, id=item_id)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, f'✅ Запись успешно удалена')
        return redirect('data_management', model_type=model_type)
    
    return render(request, 'admin/confirm_delete.html', {
        'model_type': model_type,
        'item': item
    })

@login_required
@moderator_required
def import_data(request):
    """
    Импорт данных из файла
    """
    
    if request.method == 'POST':
        form = DataImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                import_log = DataImportLog.objects.create(
                    user=request.user,
                    model_type=form.cleaned_data['model_type'],
                    status='processing',
                    import_file=request.FILES['import_file']
                )
                
                # Обработка в фоновом режиме (можно вынести в celery)
                result = process_import_file(
                    import_log, 
                    form.cleaned_data['import_mode'],
                    form.cleaned_data['validate_data']
                )
                
                import_log.status = 'completed' if result['success'] else 'failed'
                import_log.imported_count = result['imported_count']
                import_log.error_count = result['error_count']
                import_log.error_details = json.dumps(result['errors'], ensure_ascii=False)
                import_log.completed_at = timezone.now()
                import_log.save()
                
                if result['success']:
                    messages.success(request, 
                        f'✅ Импорт завершен успешно! Добавлено/обновлено: {result["imported_count"]} записей')
                else:
                    messages.warning(request,
                        f'⚠️ Импорт завершен с ошибками. Успешно: {result["imported_count"]}, Ошибок: {result["error_count"]}')
                
                return redirect('import_logs')
                
            except Exception as e:
                messages.error(request, f'❌ Ошибка при импорте: {str(e)}')
    else:
        form = DataImportForm()
    
    return render(request, 'admin/import_data.html', {'form': form})

def process_import_file(import_log, import_mode, validate_data=True):
    """
    Обработка файла импорта
    """
    result = {
        'success': False,
        'imported_count': 0,
        'error_count': 0,
        'errors': []
    }
    
    try:
        file_path = import_log.import_file.path
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Чтение файла в зависимости от формата
        if file_ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data)
        elif file_ext == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8')
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f'Неподдерживаемый формат файла: {file_ext}')
        
        # Обработка данных в зависимости от типа модели
        model_map = {
            'mineral_type': MineralType,
            'stage': Stage,
            'work': Work,
            'question': Question,
            'faq': FAQ,
        }
        
        model = model_map.get(import_log.model_type)
        if not model:
            raise ValueError(f'Неизвестный тип модели: {import_log.model_type}')
        
        # Валидация данных
        if validate_data:
            validation_errors = validate_import_data(df, import_log.model_type)
            if validation_errors:
                result['errors'] = validation_errors
                result['error_count'] = len(validation_errors)
                return result
        
        # Импорт данных
        imported_count = 0
        for _, row in df.iterrows():
            try:
                data_dict = row.to_dict()
                
                if import_mode == 'create':
                    # Создание новой записи
                    instance = model(**data_dict)
                    instance.save()
                    imported_count += 1
                    
                elif import_mode == 'update':
                    # Обновление существующей записи
                    # Предполагаем, что есть поле 'id' или 'code' для поиска
                    if 'id' in data_dict and data_dict['id']:
                        instance = model.objects.filter(id=data_dict['id']).first()
                    elif 'code' in data_dict:
                        instance = model.objects.filter(code=data_dict['code']).first()
                    else:
                        result['errors'].append(f'Нет идентификатора для обновления: {data_dict}')
                        result['error_count'] += 1
                        continue
                    
                    if instance:
                        for key, value in data_dict.items():
                            if hasattr(instance, key):
                                setattr(instance, key, value)
                        instance.save()
                        imported_count += 1
                    else:
                        result['errors'].append(f'Запись не найдена: {data_dict}')
                        result['error_count'] += 1
                        
                elif import_mode == 'upsert':
                    # Создание или обновление
                    if 'id' in data_dict and data_dict['id']:
                        instance, created = model.objects.update_or_create(
                            id=data_dict['id'],
                            defaults=data_dict
                        )
                    elif 'code' in data_dict:
                        instance, created = model.objects.update_or_create(
                            code=data_dict['code'],
                            defaults=data_dict
                        )
                    else:
                        result['errors'].append(f'Нет идентификатора для upsert: {data_dict}')
                        result['error_count'] += 1
                        continue
                    
                    imported_count += 1
                
            except Exception as e:
                result['errors'].append(f'Ошибка обработки строки {_}: {str(e)}')
                result['error_count'] += 1
        
        result['imported_count'] = imported_count
        result['success'] = imported_count > 0
        
    except Exception as e:
        result['errors'].append(f'Ошибка обработки файла: {str(e)}')
        result['error_count'] += 1
    
    return result

def validate_import_data(df, model_type):
    """
    Валидация импортируемых данных
    """
    errors = []
    
    # Базовые проверки
    if df.empty:
        errors.append('Файл пустой')
        return errors
    
    # Проверки в зависимости от типа модели
    if model_type == 'mineral_type':
        required_fields = ['name', 'code']
        for field in required_fields:
            if field not in df.columns:
                errors.append(f'Отсутствует обязательное поле: {field}')
        
        # Проверка уникальности кодов
        if 'code' in df.columns:
            duplicates = df[df['code'].duplicated()]
            if not duplicates.empty:
                errors.append(f'Найдены дублирующиеся коды: {duplicates["code"].tolist()}')
    
    elif model_type == 'stage':
        required_fields = ['mineral_type', 'name', 'code', 'order']
        for field in required_fields:
            if field not in df.columns:
                errors.append(f'Отсутствует обязательное поле: {field}')
    
    # ... дополнительные проверки для других моделей
    
    return errors

@login_required
@moderator_required
def export_data(request):
    """
    Экспорт данных
    """
    
    if request.method == 'POST':
        form = ExportDataForm(request.POST)
        if form.is_valid():
            model_type = form.cleaned_data['model_type']
            export_format = form.cleaned_data['format']
            
            # Получение данных
            model_map = {
                'mineral_type': MineralType,
                'stage': Stage,
                'work': Work,
                'question': Question,
                'faq': FAQ,
            }
            
            model = model_map.get(model_type)
            queryset = model.objects.all()
            
            # Конвертация в DataFrame
            data = list(queryset.values())
            df = pd.DataFrame(data)
            
            # Создание файла
            if export_format == 'json':
                response = HttpResponse(content_type='application/json')
                response['Content-Disposition'] = f'attachment; filename="{model_type}_export.json"'
                df.to_json(response, orient='records', force_ascii=False, indent=2)
                
            elif export_format == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{model_type}_export.csv"'
                df.to_csv(response, index=False, encoding='utf-8-sig')
                
            elif export_format == 'excel':
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = f'attachment; filename="{model_type}_export.xlsx"'
                
                with BytesIO() as bio:
                    with pd.ExcelWriter(bio, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Data')
                    response.write(bio.getvalue())
            
            return response
    else:
        form = ExportDataForm()
    
    return render(request, 'admin/export_data.html', {'form': form})

@login_required
@moderator_required
def import_logs(request):
    """
    Просмотр логов импорта
    """
    
    logs = DataImportLog.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'admin/import_logs.html', {
        'logs': logs
    })

@login_required
@moderator_required
def log_detail(request, log_id):
    """
    Детали лога импорта
    """
    
    log = get_object_or_404(DataImportLog, id=log_id, user=request.user)
    
    try:
        error_details = json.loads(log.error_details) if log.error_details else []
    except:
        error_details = []
    
    return render(request, 'admin/log_detail.html', {
        'log': log,
        'error_details': error_details
    })

@login_required
@moderator_required
def bulk_edit(request):
    """
    Массовое редактирование
    """
    
    if request.method == 'POST':
        form = BulkEditForm(request.POST)
        if form.is_valid():
            model_type = form.cleaned_data['model_type']
            ids = form.cleaned_data['ids']
            field = form.cleaned_data['field_to_edit']
            value = form.cleaned_data['new_value']
            
            model_map = {
                'mineral_type': MineralType,
                'stage': Stage,
                'work': Work,
                'question': Question,
            }
            
            model = model_map.get(model_type)
            if not model:
                messages.error(request, 'Неизвестный тип модели')
                return redirect('bulk_edit')
            
            # Проверяем, существует ли поле в модели
            if not hasattr(model(), field):
                messages.error(request, f'Поле "{field}" не существует в модели')
                return redirect('bulk_edit')
            
            # Обновляем записи
            updated_count = model.objects.filter(id__in=ids).update(**{field: value})
            
            messages.success(request, f'✅ Обновлено {updated_count} записей')
            return redirect('data_management', model_type=model_type)
    else:
        form = BulkEditForm()
    
    return render(request, 'admin/bulk_edit.html', {'form': form})

@login_required
@moderator_required
def get_model_fields(request):
    """
    API для получения полей модели (для AJAX)
    """
    
    model_type = request.GET.get('model_type')
    
    model_map = {
        'mineral_type': MineralType,
        'stage': Stage,
        'work': Work,
        'question': Question,
        'faq': FAQ,
    }
    
    if model_type not in model_map:
        return JsonResponse({'fields': []})
    
    model = model_map[model_type]
    fields = [f.name for f in model._meta.get_fields() 
              if not f.is_relation or f.one_to_one]
    
    return JsonResponse({'fields': fields})

@login_required
@moderator_required
def download_template(request, model_type):
    """
    Скачивание шаблона для импорта
    """
    
    # Создаем пример данных для шаблона
    template_data = []
    
    if model_type == 'mineral_type':
        template_data = [
            {
                'name': 'Уголь',
                'code': 'COAL',
                'description': 'Каменный уголь'
            },
            {
                'name': 'Золото',
                'code': 'GOLD', 
                'description': 'Россыпное золото'
            },
            {
                'name': 'Нефть',
                'code': 'OIL',
                'description': 'Сырая нефть'
            },
            {
                'name': 'Газ',
                'code': 'GAS',
                'description': 'Природный газ'
            }
        ]
        
    elif model_type == 'stage':
        template_data = [
            {
                'mineral_type_id': 1,
                'name': 'Геологическое изучение',
                'code': 'GEOLOGY',
                'order': 1,
                'description': 'Предварительное геологическое изучение',
                'duration_months': 6,
                'start_month': 0,
                'color': '#4285F4'
            },
            {
                'mineral_type_id': 1,
                'name': 'Лицензирование',
                'code': 'LICENSING',
                'order': 2,
                'description': 'Получение лицензии на недропользование',
                'duration_months': 12,
                'start_month': 6,
                'color': '#34A853'
            },
            {
                'mineral_type_id': 1,
                'name': 'Разведка',
                'code': 'EXPLORATION',
                'order': 3,
                'description': 'Детальная разведка месторождения',
                'duration_months': 18,
                'start_month': 18,
                'color': '#FBBC05'
            }
        ]
        
    elif model_type == 'work':
        template_data = [
            {
                'stage_id': 1,
                'number': '1.1',
                'title': 'Сбор и анализ геологической информации',
                'description': 'Сбор архивных материалов, анализ предыдущих исследований',
                'executor': 'Геологическая служба',
                'duration_months': 3,
                'start_month': 0,
                'order': 1
            },
            {
                'stage_id': 1,
                'number': '1.2',
                'title': 'Полевые геологические работы',
                'description': 'Маршрутные исследования, опробование',
                'executor': 'Полевая геологическая партия',
                'duration_months': 3,
                'start_month': 3,
                'order': 2
            },
            {
                'stage_id': 2,
                'number': '2.1',
                'title': 'Подготовка документов для лицензии',
                'description': 'Сбор необходимых документов и оформление заявки',
                'executor': 'Юридический отдел',
                'duration_months': 4,
                'start_month': 0,
                'order': 1
            }
        ]
        
    elif model_type == 'question':
        template_data = [
            {
                'text': 'Какие документы нужны для получения лицензии?',
                'code': 'LICENSE_DOCS',
                'description': 'Вопрос о необходимых документах для лицензирования',
                'mineral_types_ids': [1, 2],  # Можно указывать несколько ID через запятую
                'target_stages_ids': [2]      # ID целевых этапов
            },
            {
                'text': 'Сколько времени занимает геологическая разведка?',
                'code': 'EXPLORATION_TIME',
                'description': 'Вопрос о сроках проведения геологоразведочных работ',
                'mineral_types_ids': [1, 2, 3, 4],
                'target_stages_ids': [3, 4]
            }
        ]
        
    elif model_type == 'faq':
        template_data = [
            {
                'question': 'Как создать диаграмму Ганта?',
                'answer': 'Для создания диаграммы перейдите в раздел "Мои диаграммы" и нажмите "Создать новую". Затем выберите тип ПИ, стадию и целевой вопрос.',
                'keywords': 'создание, диаграмма, гант, инструкция',
                'order': 1,
                'is_active': True
            },
            {
                'question': 'Какой формат файлов поддерживается для импорта?',
                'answer': 'Система поддерживает импорт данных из файлов JSON, CSV и Excel (.xlsx, .xls).',
                'keywords': 'импорт, файлы, формат, json, csv, excel',
                'order': 2,
                'is_active': True
            }
        ]
    
    # Создаем DataFrame
    df = pd.DataFrame(template_data)
    
    # Создаем инструкции
    instructions_data = get_import_instructions(model_type)
    
    # Создаем ответ
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{model_type}_template.xlsx"'
    
    with BytesIO() as bio:
        with pd.ExcelWriter(bio, engine='openpyxl') as writer:
            # Лист с данными
            df.to_excel(writer, index=False, sheet_name='Данные')
            
            # Лист с инструкциями
            instructions_df = pd.DataFrame(instructions_data)
            instructions_df.to_excel(writer, index=False, sheet_name='Инструкции')
            
            # Лист со справочником ID
            if model_type in ['stage', 'work', 'question']:
                id_ref_data = get_id_reference_data(model_type)
                if id_ref_data:
                    id_ref_df = pd.DataFrame(id_ref_data)
                    id_ref_df.to_excel(writer, index=False, sheet_name='Справочник_ID')
        
        response.write(bio.getvalue())
    
    return response

def get_import_instructions(model_type):
    """Получение инструкций для импорта"""
    instructions = []
    
    if model_type == 'mineral_type':
        instructions = [
            {'Поле': 'name', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Название типа полезного ископаемого'},
            {'Поле': 'code', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Уникальный код (латинскими буквами)'},
            {'Поле': 'description', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'Описание типа ПИ'}
        ]
    elif model_type == 'stage':
        instructions = [
            {'Поле': 'mineral_type_id', 'Тип': 'integer', 'Обязательное': 'Да', 'Описание': 'ID типа ПИ (см. справочник)'},
            {'Поле': 'name', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Название этапа'},
            {'Поле': 'code', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Код этапа'},
            {'Поле': 'order', 'Тип': 'integer', 'Обязательное': 'Да', 'Описание': 'Порядковый номер этапа'},
            {'Поле': 'description', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'Описание этапа'},
            {'Поле': 'duration_months', 'Тип': 'integer', 'Обязательное': 'Нет', 'Описание': 'Длительность в месяцах (по умолчанию: 1)'},
            {'Поле': 'start_month', 'Тип': 'integer', 'Обязательное': 'Нет', 'Описание': 'Старт от начала (по умолчанию: 0)'},
            {'Поле': 'color', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'Цвет в HEX формате (например: #4285F4)'}
        ]
    elif model_type == 'work':
        instructions = [
            {'Поле': 'stage_id', 'Тип': 'integer', 'Обязательное': 'Да', 'Описание': 'ID этапа (см. справочник)'},
            {'Поле': 'number', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Номер работы (например: 1.1.1)'},
            {'Поле': 'title', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Название работы'},
            {'Поле': 'description', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'Подробное описание работы'},
            {'Поле': 'executor', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'Исполнитель работы'},
            {'Поле': 'duration_months', 'Тип': 'integer', 'Обязательное': 'Нет', 'Описание': 'Длительность в месяцах (по умолчанию: 1)'},
            {'Поле': 'start_month', 'Тип': 'integer', 'Обязательное': 'Нет', 'Описание': 'Старт от начала этапа (по умолчанию: 0)'},
            {'Поле': 'order', 'Тип': 'integer', 'Обязательное': 'Нет', 'Описание': 'Порядок в рамках этапа'}
        ]
    elif model_type == 'question':
        instructions = [
            {'Поле': 'text', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Текст вопроса'},
            {'Поле': 'code', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Уникальный код вопроса'},
            {'Поле': 'description', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'Подробное описание вопроса'},
            {'Поле': 'mineral_types_ids', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'ID типов ПИ через запятую (например: 1,2,3)'},
            {'Поле': 'target_stages_ids', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'ID целевых этапов через запятую'}
        ]
    elif model_type == 'faq':
        instructions = [
            {'Поле': 'question', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Текст вопроса'},
            {'Поле': 'answer', 'Тип': 'string', 'Обязательное': 'Да', 'Описание': 'Ответ на вопрос'},
            {'Поле': 'keywords', 'Тип': 'string', 'Обязательное': 'Нет', 'Описание': 'Ключевые слова через запятую'},
            {'Поле': 'order', 'Тип': 'integer', 'Обязательное': 'Нет', 'Описание': 'Порядок отображения'},
            {'Поле': 'is_active', 'Тип': 'boolean', 'Обязательное': 'Нет', 'Описание': 'Активен (true/false)'}
        ]
    
    return instructions

def get_id_reference_data(model_type):
    """Получение справочника ID для импорта"""
    data = []
    
    if model_type == 'stage':
        # Получаем список типов ПИ для справочника
        mineral_types = MineralType.objects.all()
        for mt in mineral_types:
            data.append({
                'ID': mt.id,
                'Тип ПИ': mt.name,
                'Код': mt.code
            })
    elif model_type == 'work':
        # Получаем список этапов для справочника
        stages = Stage.objects.select_related('mineral_type').all()
        for stage in stages:
            data.append({
                'ID': stage.id,
                'Этап': stage.name,
                'Тип ПИ': stage.mineral_type.name,
                'Код этапа': stage.code
            })
    elif model_type == 'question':
        # Получаем списки типов ПИ и этапов
        mineral_types = MineralType.objects.all()
        stages = Stage.objects.all()
        
        data.append({'СПРАВОЧНИК ТИПОВ ПИ': ''})
        for mt in mineral_types:
            data.append({
                'ID': mt.id,
                'Название': mt.name,
                'Код': mt.code
            })
        
        data.append({})  # Пустая строка
        
        data.append({'СПРАВОЧНИК ЭТАПОВ': ''})
        for stage in stages:
            data.append({
                'ID': stage.id,
                'Этап': stage.name,
                'Тип ПИ ID': stage.mineral_type.id,
                'Код': stage.code
            })
    
    return data