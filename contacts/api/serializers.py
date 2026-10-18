from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from contacts.models import Contact, ContactStatus
from contacts.phone_numbers import normalize_phone_number


class PhoneNumberField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        # Normalize before field validators so equivalent numbers share one unique value.
        try:
            return normalize_phone_number(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error


class ContactSerializer(serializers.ModelSerializer):
    phone_number = PhoneNumberField(
        max_length=Contact._meta.get_field('phone_number').max_length,
        validators=[UniqueValidator(
            queryset=Contact.objects.all(),
            message='Kontakt z takim numerem telefonu już istnieje.',
        )],
    )
    # Expose a stable status code while keeping the ForeignKey relationship.
    status = serializers.SlugRelatedField(
        slug_field='name',
        queryset=ContactStatus.objects.all(),
    )

    class Meta:
        model = Contact
        fields = (
            'id',
            'first_name',
            'last_name',
            'phone_number',
            'email',
            'city',
            'status',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')
        extra_kwargs = {
            'email': {
                'validators': [UniqueValidator(
                    queryset=Contact.objects.all(),
                    message='Kontakt z takim adresem email już istnieje.',
                )],
            },
        }
