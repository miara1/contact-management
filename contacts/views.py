from django.db.models import Q
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

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()

        # Each word must match at least one field, allowing full-name searches.
        for term in search_query.split():
            queryset = queryset.filter(
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(phone_number__icontains=term)
                | Q(email__icontains=term)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '').strip()
        return context
