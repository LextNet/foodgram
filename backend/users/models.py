from django.contrib.auth.models import AbstractUser
from django.db import models
from users.constants import (MAX_LENGTH_EMAIL, MAX_LENGTH_FIO,
                             MAX_LENGTH_USERNAME)
from users.validators import validate_username


class CustomUser(AbstractUser):
    """Переопределённая модель пользователя."""
    username = models.CharField('Пользователь', max_length=MAX_LENGTH_USERNAME,
                                unique=True,
                                validators=[validate_username],)
    first_name = models.CharField('Имя', max_length=MAX_LENGTH_FIO)
    last_name = models.CharField('Фамилия', max_length=MAX_LENGTH_FIO)
    email = models.EmailField('Адрес электронной почты',
                              max_length=MAX_LENGTH_EMAIL, unique=True)
    avatar = models.ImageField('Аватар', upload_to='users/', null=True,
                               blank=True, default='users/image.png')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['id']

    def __str__(self):
        return self.username


class Subscribe(models.Model):
    """Подписка одного пользователя на другого."""
    author = models.ForeignKey(CustomUser,
                               on_delete=models.CASCADE,
                               related_name='subscribers', db_index=True,
                               verbose_name='Автор')
    subscriber = models.ForeignKey(CustomUser,
                                   on_delete=models.CASCADE,
                                   related_name='subscriptions', db_index=True,
                                   verbose_name='Подписчик')
    created = models.DateTimeField(auto_now_add=True,
                                   verbose_name='Дата подписки')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'subscriber'],
                name='author_subscriber_relation'
            ),
            models.CheckConstraint(
                check=~models.Q(subscriber=models.F('author')),
                name='prevent_self_subscribe'
            )
        ]

    def __str__(self):
        return (f'Подписчик {self.subscriber.username} на '
                f'{self.author.username}')
