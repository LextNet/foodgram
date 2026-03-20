from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from users.models import Subscribe


User = get_user_model()


admin.site.empty_value_display = 'Не задано'


class FoodGramUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': (
            'username', 'first_name', 'last_name', 'avatar')}),
        ('Права доступа', {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'groups',
            'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name',
                       'password1', 'password2', 'avatar'),
        }),
    )


class SubscribeAdmin(admin.ModelAdmin):
    list_filter = ('created',)
    search_fields = ('subscriber__username', 'author__username')
    date_hierarchy = 'created'


admin.site.register(User, FoodGramUserAdmin)
admin.site.register(Subscribe, SubscribeAdmin)
