from django.urls import path

from .views import (
    ContactCreateView,
    ContactCSVTemplateView,
    ContactDeleteView,
    ContactImportView,
    ContactListView,
    ContactUpdateView,
)

app_name = 'contacts'

urlpatterns = [
    path('', ContactListView.as_view(), name='contact_list'),
    path('contacts/add/', ContactCreateView.as_view(), name='contact_create'),
    path('contacts/import/', ContactImportView.as_view(), name='contact_import'),
    path('contacts/template.csv', ContactCSVTemplateView.as_view(), name='contact_csv_template'),
    path('contacts/<int:pk>/edit/', ContactUpdateView.as_view(), name='contact_update'),
    path('contacts/<int:pk>/delete/', ContactDeleteView.as_view(), name='contact_delete'),
]
