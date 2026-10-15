from django.db import models


class ContactStatusChoices(models.TextChoices):
    NEW = 'new', 'Nowy'
    IN_PROGRESS = 'in_progress', 'W trakcie'
    LOST = 'lost', 'Zagubiony'
    OUTDATED = 'outdated', 'Nieaktualny'


class ContactStatus(models.Model):
    name = models.CharField(
        max_length=20,
        choices=ContactStatusChoices.choices,
        unique=True,
    )

    def __str__(self):
        return self.get_name_display()


class Contact(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    # Preserve leading zeros and the '+' prefix in phone numbers.
    phone_number = models.CharField(max_length=32, unique=True)
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=100)
    # Prevent deleting a status while it is assigned to any contact.
    status = models.ForeignKey(
        ContactStatus,
        on_delete=models.PROTECT,
        related_name='contacts',
    )
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
