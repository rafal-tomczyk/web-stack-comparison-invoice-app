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
    class Meta:
        model = Product
        fields = ['name', 'description', 'unit_type', 'net_price', 'tax_rate']
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
            'tax_rate': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
        }
        labels = {
            'name': 'Nazwa produktu',
            'description': 'Opis produktu',
            'unit_type': 'Typ jednostki',
            'net_price': 'Cena netto',
            'tax_rate': 'Stawka VAT'
        }


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

        fields = ['client_company_name', 'name', 'surname', 'nip', 'regon', 'email', 'phone_number']
        widgets = {
            'client_company_name': forms.TextInput(attrs={
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
            'client_company_name': 'Nazwa firmy klienta',
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default quantity to 1 for new/unbound forms; bound forms keep submitted value
        if not self.is_bound and (not getattr(self.instance, 'pk', None)):
            self.fields['quantity'].initial = 1


    class Meta:
        model = InvoiceItem
        fields = ['product', 'quantity', 'net_price', 'tax_rate']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'value': '1'}),
            'net_price': forms.NumberInput(attrs={'class': 'form-input'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '100'}),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=0,
    can_delete=True,
    validate_min=True,
    min_num=1
)

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields =[
            'name',
            'nip',
            'regon',
            'email'
        ]
        labels = {
            'name': 'Nazwa Firmy',
            'nip': 'NIP',
            'regon': 'REGON',
            'email': 'Email'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full mt-2',
                'placeholder': 'Nazwa firmy',
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
