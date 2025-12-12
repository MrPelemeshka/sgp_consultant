from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    """
    Кастомная модель пользователя с дополнительными ролями.
    """
    ROLE_CHOICES = (
        ('user', 'Обычный пользователь'),
        ('moderator', 'Модератор контента'),
        ('admin', 'Администратор'),
    )
    
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='user',
        verbose_name='Роль'
    )
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name='Телефон'
    )
    company = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Компания'
    )
    position = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Должность'
    )
    
    def save(self, *args, **kwargs):
        # Автоматически устанавливаем роль admin для суперпользователей
        if self.is_superuser and self.role != 'admin':
            self.role = 'admin'
        super().save(*args, **kwargs)
    
    def is_moderator(self):
        return self.role in ['moderator', 'admin']

    def is_admin(self):
        return self.role == 'admin'
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'