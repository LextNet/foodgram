from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField

from users.constants import MAX_LENGTH_USERNAME
from users.models import Subscribe
from users.validators import validate_username

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=MAX_LENGTH_USERNAME,
                                     validators=[validate_username])
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(use_url=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        ]

    def get_is_subscribed(self, instance):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            result = Subscribe.objects.filter(
                subscriber=request.user,
                author=instance
            ).exists()
        else:
            result = False
        return result

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        avatar_url = ret.get('avatar')
        if request and avatar_url:
            ret['avatar'] = self.context['request'
                                         ].build_absolute_uri(avatar_url)
        return ret


class AvatarUploadSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(
        required=True,
        use_url=True  # возвращает URL изображения при сериализации
    )

    class Meta:
        model = User
        fields = ['avatar']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        avatar_url = ret.get('avatar')
        if request and avatar_url:
            ret['avatar'] = self.context['request'
                                         ].build_absolute_uri(avatar_url)
        return ret


class SuscribeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscribe
        fields = ('id', 'author', 'subscriber')
        read_only_fields = ('user',)
