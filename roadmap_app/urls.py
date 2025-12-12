from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_gantt, name='create_gantt'),
    path('chart/<int:chart_id>/', views.view_gantt, name='view_gantt'),
    path('chart/<int:chart_id>/delete/', views.delete_gantt, name='delete_gantt'),
    path('get-stages/', views.get_filtered_stages, name='get_stages'),
    path('get-questions/', views.get_filtered_questions, name='get_questions'),
    path('get-works/', views.get_works_for_selection, name='get_works'),
    path('faq/', views.faq_search, name='faq_search'),
    
    # Административные маршруты
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/data/<str:model_type>/', views.data_management, name='data_management'),
    path('admin/data/<str:model_type>/<int:item_id>/edit/', views.edit_data, name='edit_data'),
    path('admin/data/<str:model_type>/<int:item_id>/delete/', views.delete_data, name='delete_data'),
    
    path('admin/import/', views.import_data, name='import_data'),
    path('admin/export/', views.export_data, name='export_data'),
    path('admin/import/logs/', views.import_logs, name='import_logs'),
    path('admin/import/logs/<int:log_id>/', views.log_detail, name='log_detail'),
    path('admin/bulk-edit/', views.bulk_edit, name='bulk_edit'),
    path('admin/template/<str:model_type>/', views.download_template, name='download_template'),
    
    # API для AJAX
    path('admin/api/model-fields/', views.get_model_fields, name='get_model_fields'),
]