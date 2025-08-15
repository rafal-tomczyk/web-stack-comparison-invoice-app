from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from ...models import User, Product, Client


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
            'tax_rate': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Stawka VAT (%)'
            }),
        }
        labels = {
            'name': 'Nazwa produktu',
            'description': 'Opis produktu',
            'unit_type': 'Typ jednostki',
            'net_price': 'Cena netto',
            'tax_rate': 'Stawka VAT (%)',
        }

    def clean_tax_rate(self):
        tax_rate = self.cleaned_data['tax_rate']
        if tax_rate < 0 or tax_rate > 100:
            raise forms.ValidationError(
                "Stawka VAT musi być liczbą między 0 a 100."
            )
        return tax_rate

    def clean_net_price(self):
        net_price = self.cleaned_data['net_price']
        if net_price <= 0:
            raise forms.ValidationError(
                "Cena musi być liczbą większą od 0."
            )
        return net_price

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client

        fields = ['clients_company_name', 'name', 'surname', 'nip', 'regon', 'email', 'phone_number']
        widgets = {
            'clients_company_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Nazwa firmy klienta'
            }),
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Imię'
            }),
            'surname': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Nazwisko'
            }),
            'nip': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'NIP'
            }),
            'regon': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'REGON'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Adres e-mail'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Numer telefonu'
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
