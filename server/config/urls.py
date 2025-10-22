"""
URL configuration for urban_mobility_analysis project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/mobility/', include('apps.mobility.urls')),
    path('api/poi/', include('apps.poi.urls')),
    path('api/ml/', include('apps.ml.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
]
