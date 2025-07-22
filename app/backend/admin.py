from django.contrib import admin
from .models import User, Client, Company, Invoice, InvoiceItem, Product, Address
# Register your models here.
admin.site.register(Invoice)
admin.site.register(Client)
admin.site.register(User)
admin.site.register(Product)
admin.site.register(Address)
admin.site.register(Company)
admin.site.register(InvoiceItem)
