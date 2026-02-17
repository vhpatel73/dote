from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('initiatives/', views.InitiativeListView.as_view(), name='initiative_list'),
    path('initiatives/create/', views.InitiativeCreateView.as_view(), name='initiative_create'),
    path('initiatives/<int:pk>/edit/', views.InitiativeUpdateView.as_view(), name='initiative_edit'),
    path('initiatives/<int:pk>/delete/', views.InitiativeDeleteView.as_view(), name='initiative_delete'),
    path('initiatives/<int:pk>/benefit/', views.RealizedBenefitEntryView.as_view(), name='benefit_entry'),
    path('csv/download/', views.CSVDownloadView.as_view(), name='csv_download'),
    path('csv/upload/', views.CSVUploadView.as_view(), name='csv_upload'),
    path('benefit/delete/<int:pk>/', views.RealizedBenefitDeleteView.as_view(), name='benefit_delete'),
    path('csv/sample/', views.SampleCSVDownloadView.as_view(), name='csv_sample'),
]
