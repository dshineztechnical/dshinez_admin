"""
URL configuration for attendence project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("attendenceapp.urls")),
]

# ✅ ALWAYS serve media files (for both development and production via Django)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# for testing


# from django.contrib import admin
# from django.urls import path, include
# from django.http import JsonResponse

# def api_test(request):
#     return JsonResponse({
#         'message': 'Django API is working perfectly!', 
#         'status': 'success',
#         'domain': request.get_host(),
#         'method': request.method,
#         'timestamp': '2025-10-01 12:06 PM'
#     })

# def api_health(request):
#     return JsonResponse({
#         'status': 'healthy',
#         'django_version': '4.2.24',
#         'database': 'connected',
#         'server': 'passenger'
#     })

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('api/test/', api_test, name='api_test'),
#     path('api/health/', api_health, name='api_health'),
# ]
