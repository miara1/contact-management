from django.views.generic import ListView

from .models import Contact


class ContactListView(ListView):
    template_name = 'contacts/contact_list.html'
    context_object_name = 'contacts'
    # Fetch statuses in the same query to avoid one extra query per contact.
    # Use the primary key to keep ordering stable when names are identical.
    queryset = Contact.objects.select_related('status').order_by(
        'last_name', 'first_name', 'pk'
    )
