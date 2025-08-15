#!/bin/sh

set -e


echo "Started entrypoint.sh"
echo "Connected to database..."
echo "Applying migrations..."

python manage.py tailwind install
python manage.py makemigrations
python manage.py migrate

echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser('admin@example.com', 'admin')
"

if [ "$RESET_DB" = "true" ]; then
    echo "Resetting database..."
    python manage.py flush --no-input
fi

echo "Loading initial data..."
python manage.py shell -c "
from django.core.management import call_command
from backend.models import Company
if '$RESET_DB' == 'true' or not Company.objects.exists():
    fixtures = [
        'backend/fixtures/users.json',
        'backend/fixtures/companies.json',
        'backend/fixtures/clients.json',
        'backend/fixtures/products.json',
        'backend/fixtures/invoices.json',
        'backend/fixtures/invoice_items.json',
        'backend/fixtures/addresses.json'
    ]
    for fixture in fixtures:
        call_command('loaddata', fixture)
"

echo "Starting server..."
python manage.py tailwind start &
sleep 3
python manage.py runserver 0.0.0.0:8000
