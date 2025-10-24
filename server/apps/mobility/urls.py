from django.urls import path
from . import views

urlpatterns = [
	path('sample_taxi/', views.sample_taxi_point, name='sample_taxi_point'),
]

