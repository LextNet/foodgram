import base64
import re

from django.core.exceptions import ValidationError


def validate_username(value):
    """
    Валидатор для проверки username.

    Проверяет:
    1. Что username не равен 'me' (любой регистр)
    2. Что username содержит только разрешенные символы

    Разрешенные символы: буквы, цифры, _, @, ., +, -
    """

    if value.lower() == 'me':
        raise ValidationError(
            "Имя 'me' запрещено для username.",
            code='forbidden_name'
        )

    allowed_chars_pattern = r'[\w.@+-]'

    invalid_chars = re.sub(allowed_chars_pattern, '', value)

    if invalid_chars:
        unique_invalid = sorted(set(invalid_chars))
        raise ValidationError(
            f'''Username содержит недопустимые символы:
            {",".join(unique_invalid)}. Разрешены: буквы, цифры, @, .,
             +, -, _.''',
            code='invalid_characters'
        )


def validate_base64_image(value):
    """
    Валидатор для Base64‑закодированного изображения.
    Проверяет формат, MIME‑тип и размер.
    """
    # Проверяем формат Base64 data URL
    data_url_pattern = (
        r'^data:image\/(png|jpeg|jpg|gif);base64,([A-Za-z0-9+/]+={0,2})$')
    match = re.match(data_url_pattern, value)
    if not match:
        raise ValidationError(
            'Invalid Base64 image format. Expected: "data:image/...;'
            'base64,..."'
        )

    # Извлекаем данные после префикса
    image_format, imgstr = value.split(';base64,')
    extension = image_format.split('/')[-1]

    # Декодируем Base64
    try:
        decoded_file = base64.b64decode(imgstr)
    except Exception:
        raise ValidationError('Invalid Base64 encoding.')

    # Проверка размера (5 MB)
    max_size = 5 * 1024 * 1024  # 5 MB в байтах
    if len(decoded_file) > max_size:
        raise ValidationError('Image too large. Max file size is 5 MB.')

    file_name = f'image.{extension}'
    return {
        'decoded_data': decoded_file,
        'file_name': file_name
    }
