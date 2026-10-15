from django.urls import path

from .views import ContactCreateView, ContactListView

app_name = 'contacts'

urlpatterns = [
    path('', ContactListView.as_view(), name='contact_list'),
    path('contacts/add/', ContactCreateView.as_view(), name='contact_create'),
]
