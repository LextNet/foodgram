from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from djoser.serializers import TokenCreateSerializer
from rest_framework import serializers
from users.constants import MAX_LENGTH_USERNAME
from users.models import Subscribe
from users.validators import validate_base64_image, validate_username

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=MAX_LENGTH_USERNAME,
                                     validators=[validate_username])
    is_subscribed = serializers.BooleanField(read_only=True, default=False)
    avatar = serializers.URLField(allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True,
                                     style={'input_type': 'password'},
                                     validators=[validate_password])
    username = serializers.CharField(max_length=MAX_LENGTH_USERNAME,
                                     validators=[validate_username])

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name',
                  'password']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email is already registered.')
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username is already taken.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError(
                {'current_password': 'Current password is incorrect.'}
            )

        new_password = data['new_password']

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            raise serializers.ValidationError(f'new_password: {e.messages}')
        return data

    def save(self):
        password = self.validated_data['new_password']
        user = self.context['request'].user
        user.set_password(password)
        user.save()
        return user


class Base64AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.CharField(
        required=True, validators=[validate_base64_image],
        help_text='Base64‑encoded image string with data URL prefix'
    )

    def to_internal_value(self, data):
        """
        Переопределяем метод для преобразования Base64 в файл.
        """
        # Сначала стандартная валидация
        validated_data = super().to_internal_value(data)

        # Получаем результат валидации
        avatar_value = data.get('avatar')
        validation_result = validate_base64_image(avatar_value)

        # Создаём ContentFile из декодированных данных
        extension = validation_result['extension']
        # if extension == 'jpg':
        #     extension = 'jpeg'

        file_name = f'image.{extension}'
        content_file = ContentFile(
            validation_result['decoded_data'],
            name=file_name
        )

        # Заменяем строку Base64 на ContentFile
        validated_data['avatar'] = content_file
        return validated_data


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.CharField(
        required=True,
        help_text='Base64‑encoded image string with data URL prefix'
    )

    def validate_avatar(self, value):
        # Run the custom validation
        try:
            result = validate_base64_image(value)
            # Convert decoded bytes to ContentFile
            return ContentFile(result['decoded_data'],
                               name=result['file_name'])
        except Exception as e:
            print(f"Validation error: {e}")
            raise


class CustomTokenCreateSerializer(TokenCreateSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True,
                                     style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email')
        if not email:
            raise serializers.ValidationError(
                {'email': 'Это поле обязательно.'})
        # Передаем email и password в базовый валидатор
        attrs['username'] = email  # Djoser ожидает username, подменяем
        return super().validate(attrs)

    def create(self, validated_data):
        # Удаляем username из ответа (чтобы не было в выводе)
        validated_data.pop('username', None)
        return validated_data


class SuscribeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscribe
        fields = ('id', 'author', 'subscriber')
        read_only_fields = ('user',)
