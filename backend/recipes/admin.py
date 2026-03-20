from django.contrib import admin

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)

admin.site.empty_value_display = 'Не задано'


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    verbose_name = 'Ингредиент'
    verbose_name_plural = 'Ингредиенты'
    fields = ('ingredient', 'amount')
    extra = 1
    min_num = 1
    validate_min = True


class RecipesAdmin(admin.ModelAdmin):
    list_display = ('name', 'text', 'cooking_time', 'author', 'is_favorited',
                    'get_favorites_count')
    list_editable = ('text', 'cooking_time')
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('tags',)
    readonly_fields = ('get_favorites_count',)
    filter_horizontal = ('tags', )

    inlines = [RecipeIngredientInline]

    fieldsets = (
        (None, {
            'fields': ('author', 'name', 'image', 'text', 'cooking_time')
        }),
        ('Теги', {
            'fields': ('tags',),
        }),
    )

    @admin.display(description='В избранном?', boolean=True)
    def is_favorited(self, obj):
        return obj.favorite_by.exists()

    @admin.display(description='Количество добавлений в избранное')
    def get_favorites_count(self, obj):
        return obj.favorite_by.count()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)


admin.site.register(Recipe, RecipesAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Favorite)
admin.site.register(ShoppingCart)
