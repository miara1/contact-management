from django.contrib import admin

from .forms import ContactForm
from .models import Contact, ContactStatus


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    form = ContactForm
    list_display = (
        'first_name',
        'last_name',
        'phone_number',
        'email',
        'city',
        'status',
        'formatted_created_at',
    )
    search_fields = ('first_name', 'last_name', 'phone_number', 'email', 'city')
    list_filter = ('status',)
    list_select_related = ('status',)
    readonly_fields = ('formatted_created_at',)
    ordering = ('last_name', 'first_name')

    @admin.display(description='Date added', ordering='created_at')
    def formatted_created_at(self, obj):
        # The add form has no creation date until the contact is saved.
        if obj.created_at is None:
            return None
        return obj.created_at.strftime('%d.%m.%Y')


admin.site.register(ContactStatus)
