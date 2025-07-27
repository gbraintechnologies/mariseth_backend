#!/bin/bash
# Entry script for Docker container

# Run Django-related commands only for the web service
if [ "$SERVICE_TYPE" = "web" ]; then
  python manage.py check_and_create_db
#  python manage.py collectstatic --noinput
  # Run Django makemigrations
  python manage.py fix_duplicate_farmer_emails
  python manage.py fix_duplicate_farmer_phone_numbers

  python manage.py makemigrations

  # Run Django migrate
  python manage.py migrate
  # Run Django
  # Start the Django development server
  echo "Running server on environment: $ENVIRONMENT"
  if [ "$ENVIRONMENT" = "local" ]; then
    exec uvicorn mariseth.asgi:application \
        --reload \
        --host 0.0.0.0 \
        --port 8000
  elif [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "staging" ]; then
    exec daphne -b 0.0.0.0 -p 8000 mariseth.asgi:application
  fi

# Run Celery worker for the celery service
elif [ "$SERVICE_TYPE" = "celery" ]; then
  exec celery -A mariseth worker -l info -Q "$CELERY_DEFAULT_QUEUE"

# Run Celery beat for the celery-beat service
elif [ "$SERVICE_TYPE" = "celery-beat" ]; then
  exec celery -A mariseth beat -l info

else
  echo "Unknown service type: $SERVICE_TYPE"
  exit 1
fi