from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .csv_import import create_csv_template, import_contacts
from .forms import ContactForm, ContactImportForm
from .models import Contact
from .weather import get_city_weather


class ContactListView(ListView):
    template_name = 'contacts/contact_list.html'
    context_object_name = 'contacts'
    # Fetch statuses in the same query to avoid one extra query per contact.
    queryset = Contact.objects.select_related('status')
    sort_options = {
        'last_name': 'Nazwisko: A–Z',
        '-last_name': 'Nazwisko: Z–A',
        'created_at': 'Data dodania: od najstarszych',
        '-created_at': 'Data dodania: od najnowszych',
    }

    def get_sort(self):
        sort = self.request.GET.get('sort', 'last_name')
        # Restrict URL input to supported options before using it for ordering.
        return sort if sort in self.sort_options else 'last_name'

    def get_ordering(self):
        sort = self.get_sort()
        # Use IDs to order contacts added on the same day in the chosen direction.
        if sort == '-created_at':
            return (sort, '-pk')
        if sort == 'created_at':
            return (sort, 'pk')
        return (sort, 'first_name', 'pk')

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
        context['sort_options'] = self.sort_options
        context['selected_sort'] = self.get_sort()
        context['import_form'] = ContactImportForm()
        # Consume the report once after redirecting, avoiding repeated POST uploads.
        context['import_result'] = self.request.session.pop('contact_import_result', None)
        return context


class ContactWeatherView(View):
    def get(self, request):
        cities = list(dict.fromkeys(request.GET.getlist('city')))
        if not cities or len(cities) > 3 or any(not city.strip() or len(city) > 100 for city in cities):
            return JsonResponse({'error': 'Podaj od 1 do 3 miast.'}, status=400)

        # Only cities from existing contacts may trigger external API requests.
        known_cities = set(Contact.objects.filter(city__in=cities).values_list('city', flat=True))
        if any(city not in known_cities for city in cities):
            return JsonResponse({'error': 'Miasto nie występuje na liście kontaktów.'}, status=400)

        return JsonResponse(
            {'cities': get_city_weather(cities)}, headers={'Cache-Control': 'no-store'},
        )


class ContactCreateView(CreateView):
    form_class = ContactForm
    template_name = 'contacts/contact_form.html'
    extra_context = {'form_title': 'Dodaj kontakt'}
    # Defer URL resolution until the project's URL configuration is loaded.
    success_url = reverse_lazy('contacts:contact_list')


class ContactUpdateView(UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = 'contacts/contact_form.html'
    extra_context = {'form_title': 'Edytuj kontakt'}
    success_url = reverse_lazy('contacts:contact_list')


class ContactDeleteView(DeleteView):
    model = Contact
    template_name = 'contacts/contact_confirm_delete.html'
    context_object_name = 'contact'
    success_url = reverse_lazy('contacts:contact_list')
    # Disable HTTP DELETE; deletion must use the confirmation form's POST.
    http_method_names = ['get', 'post', 'head', 'options']


class ContactImportView(View):
    def post(self, request):
        form = ContactImportForm(request.POST, request.FILES)
        if not form.is_valid():
            for error in form.errors['csv_file']:
                messages.error(request, error)
            return redirect('contacts:contact_list')

        try:
            result = import_contacts(form.cleaned_data['csv_file'])
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            request.session['contact_import_result'] = result

        return redirect('contacts:contact_list')


class ContactCSVTemplateView(View):
    def get(self, request):
        return HttpResponse(
            create_csv_template(),
            content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': 'attachment; filename="contacts_template.csv"'},
        )
