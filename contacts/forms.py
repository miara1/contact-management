from django import forms
from django.core.validators import FileExtensionValidator

from .models import Contact
from .phone_numbers import POLISH_EMERGENCY_NUMBERS, normalize_phone_number


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
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'type': 'tel',
                'autocomplete': 'tel',
                'data-polish-emergency-numbers': ' '.join(POLISH_EMERGENCY_NUMBERS),
            }),
        }
        help_texts = {
            'phone_number': (
                'Polskie numery alarmowe, np. 112 i 997, podaj bez prefiksu kraju. '
                'Dla pozostałych numerów bez prefiksu przyjmujemy +48. '
                'Numery zagraniczne podaj z + lub 00.'
            ),
        }
        error_messages = {
            'phone_number': {'unique': 'Kontakt z takim numerem telefonu już istnieje.'},
            'email': {'unique': 'Kontakt z takim adresem email już istnieje.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep the default widgets and add Bootstrap classes for consistent styling.
        for field in self.fields.values():
            field.widget.attrs['class'] = (
                'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            )

    def clean_phone_number(self):
        # Field cleaning runs before ModelForm checks uniqueness against the database.
        return normalize_phone_number(self.cleaned_data['phone_number'])


class ContactImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Plik CSV',
        validators=[FileExtensionValidator(
            allowed_extensions=['csv'],
            message='Wybierz plik z rozszerzeniem .csv.',
        )],
        error_messages={'required': 'Wybierz plik CSV do importu.'},
        widget=forms.ClearableFileInput(attrs={
            'accept': '.csv,text/csv',
            'class': 'form-control',
        }),
    )
