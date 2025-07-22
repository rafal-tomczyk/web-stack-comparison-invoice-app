#!/bin/sh

set -e

echo "Waiting for database..."

echo "Applying migrations..."
python manage.py makemigrations
python manage.py migrate

echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser('admin@example.com', 'admin')
"

echo "Loading initial data if no companies..."
python manage.py shell -c "
from backend.models import Company
if not Company.objects.exists():
    from django.core.management import call_command
    call_command('loaddata', 'backend/fixtures/initial_data.json')
"

echo "Starting server..."
exec "$@"
