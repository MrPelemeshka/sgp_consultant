from django.db import models
from django.conf import settings

class MineralType(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Тип полезного ископаемого'
        verbose_name_plural = 'Типы полезных ископаемых'

class Stage(models.Model):
    """
    Этап проекта (например: Изучение, Лицензирование, Разведка, Разработка)
    """
    mineral_type = models.ForeignKey(
        MineralType,
        on_delete=models.CASCADE,
        related_name='stages',
        verbose_name='Тип ПИ'
    )
    name = models.CharField(max_length=200, verbose_name='Название этапа')
    code = models.CharField(max_length=50, verbose_name='Код этапа')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    # Временные параметры
    duration_months = models.IntegerField(default=1, verbose_name='Длительность этапа (месяцев)')
    start_month = models.IntegerField(default=0, verbose_name='Старт этапа (месяц от начала)')
    
    # Цвет для отображения
    color = models.CharField(max_length=7, default='#0070C0', verbose_name='Цвет')
    
    # Зависимости от других этапов
    depends_on = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        verbose_name='Зависит от',
        help_text='Этапы, которые должны быть завершены перед началом этого',
        related_name='dependent_stages'
    )
    
    def __str__(self):
        return f"{self.mineral_type.name} - {self.name}"
    
    class Meta:
        verbose_name = 'Этап'
        verbose_name_plural = 'Этапы'
        ordering = ['order']
        unique_together = ['mineral_type', 'code']

class Work(models.Model):
    """
    Конкретная работа внутри этапа
    """
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name='works',
        verbose_name='Этап'
    )
    
    number = models.CharField(max_length=20, verbose_name='Номер работы')
    title = models.CharField(max_length=500, verbose_name='Название работы')
    description = models.TextField(blank=True, verbose_name='Описание работы')
    executor = models.CharField(max_length=300, verbose_name='Исполнитель')
    
    # Временные параметры конкретной работы
    duration_months = models.IntegerField(default=1, verbose_name='Длительность (месяцев)')
    start_month = models.IntegerField(default=0, verbose_name='Старт (месяц от начала этапа)')
    
    order = models.IntegerField(default=0, verbose_name='Порядок в этапе')
    
    def __str__(self):
        return f"{self.number} - {self.title}"
    
    class Meta:
        verbose_name = 'Работа'
        verbose_name_plural = 'Работы'
        ordering = ['order']
        unique_together = ['stage', 'number']

class Question(models.Model):
    """
    Вопросы, которые пользователь хочет решить
    Вопрос ограничивает, ДО КАКОГО ЭТАПА нужно строить диаграмму
    """
    text = models.CharField(max_length=500, verbose_name='Текст вопроса')
    code = models.CharField(max_length=50, unique=True, verbose_name='Код вопроса')
    description = models.TextField(blank=True, verbose_name='Описание вопроса')
    
    # С какими типами ПИ связан вопрос
    mineral_types = models.ManyToManyField(
        MineralType,
        related_name='questions',
        verbose_name='Доступно для типов ПИ'
    )
    
    # До каких этапов нужно дойти для решения этого вопроса
    target_stages = models.ManyToManyField(
        Stage,
        related_name='target_questions',
        verbose_name='Целевые этапы',
        help_text='До каких этапов нужно дойти для решения вопроса'
    )
    
    def __str__(self):
        return self.text
    
    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

class UserGanttChart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gantt_charts',
        verbose_name='Пользователь'
    )
    title = models.CharField(max_length=200, verbose_name='Название проекта')
    
    # Выбранные параметры
    mineral_type = models.ForeignKey(
        MineralType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Тип полезного ископаемого'
    )
    start_stage = models.ForeignKey(
        Stage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='start_charts',
        verbose_name='Начальный этап'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Целевой вопрос'
    )
    
    # Содержимое диаграммы
    chart_data = models.JSONField(default=dict, verbose_name='Данные диаграммы')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    class Meta:
        verbose_name = 'Диаграмма Ганта'
        verbose_name_plural = 'Диаграммы Ганта'
        ordering = ['-created_at']

class FAQ(models.Model):
    """
    Часто задаваемые вопросы
    """
    question = models.CharField(max_length=500, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')
    keywords = models.TextField(
        verbose_name='Ключевые слова (через запятую)',
        help_text='Слова для поиска, разделенные запятыми'
    )
    order = models.IntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_keywords_list(self):
        return [k.strip() for k in self.keywords.split(',')]
    
    def __str__(self):
        return self.question
    
    class Meta:
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'
        ordering = ['order']

class DataImportTemplate(models.Model):
    """
    Шаблон для импорта данных
    """
    name = models.CharField(max_length=200, verbose_name='Название шаблона')
    model_type = models.CharField(
        max_length=50,
        choices=[
            ('mineral_type', 'Тип полезного ископаемого'),
            ('stage', 'Этап'),
            ('work', 'Работа'),
            ('question', 'Вопрос'),
            ('faq', 'FAQ'),
        ],
        verbose_name='Тип данных'
    )
    template_file = models.FileField(
        upload_to='import_templates/',
        verbose_name='Файл шаблона'
    )
    description = models.TextField(verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_model_type_display()})"
    
    class Meta:
        verbose_name = 'Шаблон импорта'
        verbose_name_plural = 'Шаблоны импорта'

class DataImportLog(models.Model):
    """
    Лог импорта данных
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    model_type = models.CharField(
        max_length=50,
        choices=[
            ('mineral_type', 'Тип полезного ископаемого'),
            ('stage', 'Этап'),
            ('work', 'Работа'),
            ('question', 'Вопрос'),
            ('faq', 'FAQ'),
        ],
        verbose_name='Тип данных'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'В ожидании'),
            ('processing', 'В обработке'),
            ('completed', 'Завершено'),
            ('failed', 'Ошибка'),
        ],
        default='pending',
        verbose_name='Статус'
    )
    imported_count = models.IntegerField(default=0, verbose_name='Импортировано записей')
    error_count = models.IntegerField(default=0, verbose_name='Ошибок')
    error_details = models.TextField(blank=True, verbose_name='Детали ошибок')
    import_file = models.FileField(
        upload_to='imports/',
        null=True,
        blank=True,
        verbose_name='Файл импорта'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_model_type_display()} - {self.created_at}"
    
    class Meta:
        verbose_name = 'Лог импорта'
        verbose_name_plural = 'Логи импорта'
        ordering = ['-created_at']

class DataValidationRule(models.Model):
    """
    Правила валидации данных
    """
    model_type = models.CharField(
        max_length=50,
        choices=[
            ('mineral_type', 'Тип полезного ископаемого'),
            ('stage', 'Этап'),
            ('work', 'Работа'),
            ('question', 'Вопрос'),
        ],
        verbose_name='Тип данных'
    )
    field_name = models.CharField(max_length=100, verbose_name='Поле')
    rule_type = models.CharField(
        max_length=50,
        choices=[
            ('required', 'Обязательное поле'),
            ('unique', 'Уникальное значение'),
            ('min_length', 'Минимальная длина'),
            ('max_length', 'Максимальная длина'),
            ('regex', 'Регулярное выражение'),
        ],
        verbose_name='Тип правила'
    )
    rule_value = models.CharField(max_length=500, verbose_name='Значение правила')
    error_message = models.CharField(max_length=500, verbose_name='Сообщение об ошибке')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    
    def __str__(self):
        return f"{self.get_model_type_display()} - {self.field_name} - {self.rule_type}"
    
    class Meta:
        verbose_name = 'Правило валидации'
        verbose_name_plural = 'Правила валидации'