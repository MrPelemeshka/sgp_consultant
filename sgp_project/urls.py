from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from roadmap_app.views import HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('users/', include('users_app.urls')),
    path('roadmap/', include('roadmap_app.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)