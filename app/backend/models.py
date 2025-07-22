from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Company(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='companies'
    )
    name = models.CharField(max_length=225)
    nip = models.CharField(max_length=10)
    regon = models.CharField(max_length=14, blank=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Client(models.Model):
    company = models.ForeignKey(
        "Company",
        on_delete=models.PROTECT,
        related_name="clients"
    )
    clients_company_name = models.CharField(
        max_length=255,
        blank=True,
    )
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100, blank=True)
    nip = models.CharField(max_length=20, blank=True)
    regon = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        if self.clients_company_name:
            return self.clients_company_name
        return f"{self.name} {self.surname or ''}".strip()


class Product(models.Model):
    UNIT_CHOICES = [
        ('pcs', 'Sztuki'),
        ('h', 'Godziny'),
        ('kg', 'Kilogramy'),
    ]

    company = models.ForeignKey(
        "Company",
        on_delete=models.PROTECT,
        related_name="products"
    )
    name = models.CharField(max_length=225)
    description = models.TextField()
    unit_type = models.CharField(max_length=10, choices=UNIT_CHOICES)
    net_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    PAYMENT_METHODS =[
        ('cash', 'Cash'),
        ('transfer', 'Transfer'),
        ('card', 'Card'),
    ]

    company = models.ForeignKey(
        "Company",
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    client = models.ForeignKey(
        "Client",
        on_delete=models.SET_NULL,
        null=True,
        related_name='invoices'
    )
    number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField()
    due_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    paid = models.BooleanField(default=False)
    note = models.TextField(blank=True)
    total_net = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        editable=False
    )
    total_tax = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        editable=False
    )
    total_gross = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        editable=False
    )

    def update_totals(self):
        items = self.items.all()
        self.total_net = sum(item.net_total for item in items)
        self.total_tax = sum(item.tax_amount for item in items)
        self.total_gross = sum(item.gross_total for item in items)
        self.save(update_fields=['total_net', 'total_tax', 'total_gross'])

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.PROTECT
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    net_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    tax_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True
    )
    net_total = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    gross_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name}, qt: {self.quantity}"

    def save(self, *args, **kwargs):
        if self.net_price is None:
            self.net_price = self.product.net_price
        if self.tax_rate is None:
            self.tax_rate = self.product.tax_rate

        self.net_total = self.quantity * self.net_price
        self.tax_amount = self.net_total * (self.tax_rate / 100)
        self.gross_total = self.net_total + self.tax_amount
        super().save(*args, **kwargs)

        self.invoice.update_totals()


class Address(models.Model):
    USER_ADDRESS_TYPES = [
        ('user', 'User'),
        ('company', 'Company'),
        ('client', 'Client'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    address_type = models.CharField(max_length=20, choices=USER_ADDRESS_TYPES)
    region = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=100)
    number = models.CharField(max_length=20)
    apartment = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        parts = [self.street, self.number]
        if self.apartment:
            parts.append(f"apt. {self.apartment}")
        parts.append(self.city)
        return ", ".join(parts)
