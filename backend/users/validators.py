from django.core.exceptions import ValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator

from users.constants import FORBIDEN_NAME


def validate_username(value):
    """
    Валидатор для проверки username.

    Проверяет:
    1. Что username не равен 'me' (любой регистр)
    2. Что username содержит только разрешенные символы

    Разрешенные символы: буквы, цифры, _, @, ., +, -
    """
    # Применяем стандартную проверку UnicodeUsernameValidator
    validator = UnicodeUsernameValidator()
    validator(value)

    if value.lower() == FORBIDEN_NAME:
        raise ValidationError(
            f'Имя {FORBIDEN_NAME} запрещено для username.',
            code='forbidden_name'
        )
