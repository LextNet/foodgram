from django.contrib import admin

from recipes.models import Favourite, Ingredient, Recipe, ShoppingCart, Tag

admin.site.empty_value_display = 'Не задано'


class RecipesAdmin(admin.ModelAdmin):
    list_display = ('name', 'text', 'cooking_time', 'author', 'is_favorited',
                    'get_favorites_count')
    list_editable = ('text', 'cooking_time')
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('tags',)
    readonly_fields = ('get_favorites_count',)
    filter_horizontal = ('tags', )

    @admin.display(description='В избранном?', boolean=True)
    def is_favorited(self, obj):
        return obj.favorited_by.exists()

    @admin.display(description='Количество добавлений в избранное')
    def get_favorites_count(self, obj):
        return obj.favorited_by.count()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)


admin.site.register(Recipe, RecipesAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Favourite)
admin.site.register(ShoppingCart)
