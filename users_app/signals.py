from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def set_default_role_for_admin(sender, instance, created, **kwargs):
    """
    Автоматически устанавливаем роль 'admin' для суперпользователей
    """
    if created and instance.is_superuser and not instance.role:
        instance.role = 'admin'
        instance.save(update_fields=['role'])