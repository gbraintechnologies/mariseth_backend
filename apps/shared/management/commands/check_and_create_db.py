import os
import psycopg2
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Checks if the database exists and creates it if necessary.'

    def handle(self, *args, **kwargs):
        db_name = os.getenv('DB_NAME', settings.DATABASES['default']['NAME'])
        db_user = os.getenv('DB_USER', settings.DATABASES['default']['USER'])
        db_password = os.getenv('DB_PASSWORD', settings.DATABASES['default']['PASSWORD'])
        db_host = os.getenv('DB_HOST', settings.DATABASES['default']['HOST'])
        db_port = os.getenv('DB_PORT', settings.DATABASES['default']['PORT'])

        if not db_name:
            self.stderr.write('Database name must be set in the environment variable or settings.')
            return

        # Connect to the default database to check/create the target database
        try:
            connection = psycopg2.connect(
                dbname="postgres",  # Default database for administrative tasks
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
            )
            connection.autocommit = True
            cursor = connection.cursor()

            # Check if the database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
            exists = cursor.fetchone()

            if not exists:
                self.stdout.write(f"Database '{db_name}' does not exist. Creating it...")
                cursor.execute(f'CREATE DATABASE "{db_name}";')
                self.stdout.write(f"Database '{db_name}' created successfully.")

        except psycopg2.OperationalError as e:
            self.stderr.write(f"Error while checking or creating the database: {e}")
            return
        finally:
            if 'connection' in locals():
                cursor.close()
                connection.close()

        self.stdout.write("Running migrations...")
        os.system('python manage.py migrate')
        self.stdout.write("Migrations applied successfully.")
