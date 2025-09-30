from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_view, name="upload"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("job/<int:job_id>/", views.job_detail_view, name="job_detail"),  # ’Ç‰Á
]
