import json
from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings
import uuid

from django.db.models import Max, Sum, F, Count
from django.db.models.functions import TruncMonth, Round
from phonenumber_field.modelfields import PhoneNumberField


def validate_nip(nip):
    if len(nip) != 10 or not nip.isdigit():
        raise ValidationError("NIP musi składać się z 10 cyfr.")
    weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    control_sum = sum([int(nip[i]) * weights[i] for i in range(9)])
    if control_sum % 11 != int(nip[9]):
        raise ValidationError("NIP jest nieprawidłowy.")

def validate_regon(regon):
    if len(regon) not in (9, 14) or not regon.isdigit():
        raise ValidationError("REGON musi zawierać 9 lub 14 cyfr.")
    weights_9 = [8, 9, 2, 3, 4, 5, 6, 7]
    weights_14 = [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 0, 5, 9]

    if len(regon) == 9:
        control_sum = sum([int(regon[i]) * weights_9[i] for i in range(8)])
        if control_sum % 11 != int(regon[8]):
            raise ValidationError("REGON jest nieprawidłowy.")
    elif len(regon) == 14:
        control_sum = sum([int(regon[i]) * weights_14[i] for i in range(13)])
        if control_sum % 11 != int(regon[13]):
            raise ValidationError("REGON jest nieprawidłowy.")


class UUIDModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    class Meta:
        abstract = True

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



class Company(UUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='companies',
        blank=False,
        null=False
    )
    name = models.CharField(max_length=225, blank=False)
    nip = models.CharField(
        max_length=10,
        blank=False,
        unique=True,
        validators=[validate_nip]
    )
    regon = models.CharField(max_length=14, blank=True, validators=[validate_regon])
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_latest_invoices(self, limit=10):
        return self.invoices.order_by("-issue_date")[:limit]

    def get_top_clients(self, limit=5):
        return (
            self.clients
            .annotate(total_spent=Sum("invoices__total_gross"))
            .filter(total_spent__isnull=False)
            .order_by("-total_spent")[:limit]
    )

    def get_monthly_revenues(self, year=None):
        if year is None:
            year = datetime.now().year

        monthly_revenues = [0] * 12

        revenues = self.invoices.filter(
            issue_date__year=year
        ).annotate(
            month=TruncMonth('issue_date')
        ).values('month').annotate(
            total_revenue=Sum('total_gross')
        ).order_by('month')

        for revenue in revenues:
            month_index = revenue['month'].month - 1
            monthly_revenues[month_index] = revenue['total_revenue'] or 0

        return monthly_revenues

    def get_monthly_revenues_json(self, year=None):
        return json.dumps(self.get_monthly_revenues(year), default=str)

    def get_current_monthly_revenue(self):
        now = datetime.now()
        monthly_revenues = self.get_monthly_revenues(now.year)
        return monthly_revenues[now.month - 1]

    def get_yearly_revenue(self, year=None):
        if year is None:
            year = datetime.now().year

        return self.invoices.filter(
            issue_date__year=year
        ).aggregate(total_revenue=Sum('total_gross'))['total_revenue'] or 0

    def get_top_products(self, limit=5):
        return (Product.objects.filter(
            invoiceitem__invoice__company=self
        ).annotate(
            total_sold=Sum('invoiceitem__quantity'),
            total_revenue=Round(Sum(
                F('invoiceitem__net_price') * F('invoiceitem__quantity')
            ), 2)
        ).order_by('-total_sold')[:limit])

    def __str__(self):
        return self.name


class Client(UUIDModel):
    company = models.ForeignKey(
        "Company",
        on_delete=models.PROTECT,
        related_name="clients"
    )
    client_company_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100, blank=True, null=True)
    nip = models.CharField(max_length=20, blank=True, null=True, validators=[validate_nip])
    regon = models.CharField(max_length=20, blank=True, null=True, validators=[validate_regon])
    email = models.EmailField(blank=True, null=True)
    phone_number = PhoneNumberField(region="PL", blank=True, null=True)

    def __str__(self):
        if self.client_company_name:
            return self.client_company_name
        return f"{self.name} {self.surname or ''}".strip()



class Product(UUIDModel):
    UNIT_CHOICES = [
        ('pcs', 'Sztuki'),
        ('h', 'Godziny'),
        ('kg', 'Kilogramy'),
    ]

    TAX_RATE_CHOICES = [
        (0, '0%'),
        (5, '5%'),
        (8, '8%'),
        (23, '23%'),
        (0, 'zw.')
    ]

    company = models.ForeignKey(
        "Company",
        on_delete=models.PROTECT,
        related_name="products"
    )
    name = models.CharField(max_length=225)
    description = models.TextField(blank=True)
    unit_type = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default='pcs'
    )
    net_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.IntegerField(
        choices=TAX_RATE_CHOICES,
        default=23
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def calculate_brutto(self):
        return self.net_price * (1 + self.tax_rate / 100)

class Invoice(UUIDModel):
    PAYMENT_METHODS =[
        ('cash', 'Gotówka'),
        ('transfer', 'Przelew Bankowy'),
        ('card', 'Karta Płatnicza'),
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

    def generate_invoice_number(self):
        """Generates the invoice number in the format: number/month/year."""
        today = date.today()
        current_month = today.month
        current_year = today.year

        last_invoice = Invoice.objects.filter(
            company=self.company_id,
            issue_date__month=current_month,
            issue_date__year=current_year
        ).aggregate(Max('number'))

        last_number = 0
        if last_invoice['number__max']:
            last_number = int(last_invoice['number__max'].split('/')[0]) + 1

        new_number = last_number + 1

        return f"{new_number}/{current_month:02d}/{current_year}"

    def save(self, *args, **kwargs):
        """Generate an automatic invoice number if number is not set."""
        if not self.number:
            self.number = self.generate_invoice_number()
        super().save(*args, **kwargs)

class InvoiceItem(UUIDModel):
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


class Address(UUIDModel):
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
