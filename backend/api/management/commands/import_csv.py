"""Management-команда для импорта данных из CSV-файлов в БД."""
import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from recipes.models import Ingredient


class Command(BaseCommand):
    """Команда импорта данных из CSV-файлов в базу данных."""

    help = 'Import data from CSV files into database'

    def add_arguments(self, parser):
        """Добавляет аргументы команды."""
        parser.add_argument(
            '--path',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'data'),
            help='Path to directory with CSV files'
        )

    def handle(self, *args, **options):
        """Запускает процесс импорта данных."""
        csv_path = options['path']

        self.stdout.write(self.style.SUCCESS('Starting CSV import...'))

        try:
            with transaction.atomic():
                print(csv_path)
                self.import_ingredients(csv_path)

            self.stdout.write(
                self.style.SUCCESS('Successfully imported all CSV data!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during import: {str(e)}')
            )
            raise

    def import_ingredients(self, csv_path):
        """Импортирует ингредиенты из файла ingredients.csv."""
        file_path = os.path.join(csv_path, 'ingredients.csv')
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.WARNING(f'File {file_path} not found, skipping...')
            )
            return

        self.stdout.write('Importing ingredients...')
        count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) != 2:
                    continue  # пропустить повреждённые строки
                name, unit = row
                _, created = Ingredient.objects.get_or_create(
                    name=name.strip(),
                    measurement_unit=unit.strip()
                )
                if created:
                    count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Imported {count} ingredients')
        )
