from django import forms

from .models import Contact


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        # Explicit fields keep future model additions out of the form by default.
        fields = (
            'first_name',
            'last_name',
            'phone_number',
            'email',
            'city',
            'status',
        )
        labels = {
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
            'phone_number': 'Numer telefonu',
            'email': 'Adres email',
            'city': 'Miasto',
            'status': 'Status',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep the default widgets and add Bootstrap classes for consistent styling.
        for field in self.fields.values():
            field.widget.attrs['class'] = (
                'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            )
