from rest_framework import generics

from contacts.models import Contact

from .serializers import ContactSerializer


class ContactListCreateAPIView(generics.ListCreateAPIView):
    queryset = Contact.objects.select_related('status').order_by('last_name', 'first_name', 'pk')
    serializer_class = ContactSerializer
    pagination_class = None
    http_method_names = ['get', 'post', 'head', 'options']


class ContactDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.select_related('status')
    serializer_class = ContactSerializer
    # The required detail endpoint supports full updates and deletion only.
    http_method_names = ['put', 'delete', 'options']
