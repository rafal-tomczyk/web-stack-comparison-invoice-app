import logging
from datetime import date, timedelta, datetime

from dateutil.utils import today
from django import forms
from django.core import validators
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory

from ...models import User, Product, Client, Invoice, Company, InvoiceItem
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget



class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Adres e-mail"
        self.fields["password1"].label = "Hasło"
        self.fields["password2"].label = "Potwierdź hasło"

        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Nazwa użytkownika',
            'class': 'input input-bordered w-full p-6 mt-8',
        }),
        label="",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Hasło',
            'class': 'input input-bordered w-full p-6 mt-4',
        }),
        label="",
    )


class ProductForm(forms.ModelForm):
    VAT_CHOICES = [
        (23, "23%"),
        (8, "8%"),
        (5, "5%"),
        (0, "0%"),
        ("custom", "Inna (wpisz ponizej")
    ]

    tax_rate_choice = forms.ChoiceField(
        choices=VAT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full',
        }),
        label="Stawka VAT (%)"
    )
    custom_tax_rate = forms.DecimalField(
        max_value=100,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full mt-2',
            'placeholder': 'Wpisz niestandardową stawkę VAT (%)',
            'step': '0.01'
        }),
        label="Niesterowana stawka"
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'unit_type', 'net_price']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Nazwa produktu'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'placeholder': 'Opis produktu',
                'rows': 4
            }),
            'unit_type': forms.Select(attrs={
                'class': 'select select-bordered w-full',
            }),
            'net_price': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Cena netto'
            }),
        }
        labels = {
            'name': 'Nazwa produktu',
            'description': 'Opis produktu',
            'unit_type': 'Typ jednostki',
            'net_price': 'Cena netto',
        }

    def clean(self):
        cleaned_data = super().clean()
        tax_rate_choice = cleaned_data.get("tax_rate_choice")
        custom_tax_rate = cleaned_data.get("custom_tax_rate")

        # Walidacja opcji niestandardowej
        if tax_rate_choice == 'custom':
            if custom_tax_rate is None:
                raise forms.ValidationError(
                    "Wybierz wartość VAT lub wpisz stawkę ręcznie.")
            if custom_tax_rate < 0 or custom_tax_rate > 100:
                raise forms.ValidationError(
                    "Stawka VAT musi być między 0 a 100.")
            cleaned_data['tax_rate'] = custom_tax_rate
        else:
            cleaned_data['tax_rate'] = int(tax_rate_choice)

        return cleaned_data

    def save(self, commit = True):
        instance = super().save(commit=False)
        tax_rate_choice = self.cleaned_data.get("tax_rate_choice")
        custom_tax_rate = self.cleaned_data.get("custom_tax_rate")

        if tax_rate_choice == 'custom' and custom_tax_rate is not None:
            instance.tax_rate = custom_tax_rate
        else:
            instance.tax_rate = int(tax_rate_choice)

        if commit:
            instance.save()
        return instance


class ClientForm(forms.ModelForm):
    phone_number = PhoneNumberField(
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Numer telefonu',
            'type': 'tel'
        }),
        label="Numer telefonu",
        region="PL",
        required=False
    )

    class Meta:
        model = Client

        fields = ['clients_company_name', 'name', 'surname', 'nip', 'regon', 'email', 'phone_number']
        widgets = {
            'clients_company_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full mt-2',
                'placeholder': 'Nazwa firmy klienta',
            }),
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full mt-2',
                'placeholder': 'Imię'
            }),
            'surname': forms.TextInput(attrs={
                'class': 'input input-bordered w-full mt-2',
                'placeholder': 'Nazwisko'
            }),
            'nip': forms.TextInput(attrs={
                'class': 'input input-bordered w-full mt-2',
                'placeholder': 'NIP'
            }),
            'regon': forms.TextInput(attrs={
                'class': 'input input-bordered w-full mt-2',
                'placeholder': 'REGON'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full mt-2',
                'placeholder': 'Adres e-mail'
            }),
        }
        labels = {
            'clients_company_name': 'Nazwa firmy klienta',
            'name': 'Imię',
            'surname': 'Nazwisko',
            'nip': 'NIP',
            'regon': 'REGON',
            'email': 'E-mail',
            'phone_number': 'Numer telefonu',
        }

    def clean_name(self):
        first_name: str | None = self.cleaned_data.get("name")
        if first_name and not first_name.isalpha():
            raise forms.ValidationError("Imię może zawierać tylko litery.")

        if first_name:
            return first_name.capitalize()
        else:
            return first_name

    def clean_surname(self) -> str:
        surname: str = self.cleaned_data.get("surname", "")
        if surname and not surname.isalpha():
            raise forms.ValidationError("Nazwisko może zawierać tylko litery.")

        if surname:
            return surname.capitalize()
        else:
            return surname


    def clean(self):
        cleaned_data = super().clean()

        client_company_name = cleaned_data.get("client_company_name")
        name = cleaned_data.get('name')
        surname = cleaned_data.get('surname')
        nip = cleaned_data.get('nip')
        regon = cleaned_data.get('regon')
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone_number')

        if client_company_name:
            if not nip:
                self.add_error('nip', 'NIP jest wymagany dla firmy.')
            if not regon:
                self.add_error('regon', 'REGON jest wymagany dla firmy.')
        else:
            if not name:
                self.add_error('name', 'Osoba prywatna musi posiadać imię.')
            if not surname:
                self.add_error('surname', 'Osoba prywatna musi posiadać nazwisko.')
            if nip:
                self.add_error('nip', 'Osoba prywatna nie moze posiadać numeru NIP.')
            if regon:
                self.add_error('regon', 'Osoba prywatna nie moze posiadać numeru REGON.')

        if not email and not phone:
            raise ValidationError('Musisz podać przynajmniej jeden sposób kontaktu.')

        return cleaned_data



class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'number',
            'client',
            'issue_date',
            'due_date',
            'payment_method',
            'note',
            'paid',
        ]
        labels = {
            'number': 'Numer Faktury',
            'client': 'Klient',
            'issue_date': 'Data wystawienia',
            'due_date': 'Data ostatecznego terminu zapłaty',
            'payment_method': 'Metoda Płatności',
            'note': 'Notatka',
            'paid': 'Opłacona',
        }
        widgets = {
            'number': forms.TextInput(
                attrs={'class': 'input input-bordered w-full',
                       'placeholder': 'Numer faktury'}),
            'client': forms.Select(
                attrs={'class': 'select select-bordered w-full'}),
            'issue_date': forms.DateInput(
                attrs={'class': 'input input-bordered w-full',
                       'type': 'date'}),
            'due_date': forms.DateInput(
                attrs={'class': 'input input-bordered w-full',
                       'type': 'date'}),
            'payment_method': forms.Select(
                attrs={'class': 'select select-bordered w-full'}),
            'note': forms.Textarea(
                attrs={'class': 'textarea textarea-bordered w-full',
                       'rows': 3}),
            'paid': forms.CheckboxInput(
                attrs={'class': 'checkbox checkbox-primary '}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = datetime.today()
        current_month_invoices = Invoice.objects.filter(
            issue_date__year=today.year,
            issue_date__month=today.month,
        ).order_by('-number')

        if current_month_invoices.exists():
            last_invoice = current_month_invoices.first()
            last_number = int(last_invoice.number.split('/')[0])
            new_number = last_number + 1
        else:
            new_number = 1

        generated_number = f"{new_number}/{today.month}/{today.year}"
        self.fields['number'].initial = generated_number

        issue_date = self.data.get('issue_date')
        if issue_date:
            issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
        else:
            issue_date = datetime.today().date()

        self.fields['issue_date'].initial = issue_date
        self.fields['due_date'].initial = issue_date + timedelta(days=14)


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['product', 'quantity', 'net_price', 'tax_rate']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input'}),
            'net_price': forms.NumberInput(attrs={'class': 'form-input'}),
            'tax_rate': forms.Select(attrs={'class': 'form-select'}),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True,
    validate_min=True
)
