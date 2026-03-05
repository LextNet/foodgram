from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser, Subscribe

admin.site.empty_value_display = 'Не задано'


class FoodGramUserAdmin(UserAdmin):
    search_fields = ('username', 'email')
    UserAdmin.fieldsets += (
        (None, {'fields': ('avatar',)}),
    )
    ordering = ('username',)


class SubscribeAdmin(admin.ModelAdmin):
    list_filter = ('created',)
    search_fields = ('subscriber__username', 'author__username')
    date_hierarchy = 'created'


admin.site.register(CustomUser, FoodGramUserAdmin)
admin.site.register(Subscribe, SubscribeAdmin)
