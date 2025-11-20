"""
URL configuration for urban_mobility_analysis project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.mobility.urls')),
]
