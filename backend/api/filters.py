from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe, Tag


class RecipeFilter(filters.FilterSet):
    """FilterSet для рецептов."""
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )
    author = filters.NumberFilter(field_name='author_id')
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author', 'tags']

    def filter_is_favorited(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(
                favorited_by__user=self.request.user
            )
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(
                shoppingcart__user=self.request.user
            )
        return queryset


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )  # регистронезависимый поиск по началу

    class Meta:
        model = Ingredient
        fields = ['name']
