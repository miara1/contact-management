from django.urls import path

from .views import ContactDetailAPIView, ContactListCreateAPIView

app_name = 'contacts_api'

urlpatterns = [
    path('contacts/', ContactListCreateAPIView.as_view(), name='contact_list'),
    path('contacts/<int:pk>/', ContactDetailAPIView.as_view(), name='contact_detail'),
]
