from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

from recipes.constants import (MAX_LENGTH_INGREDIENT, MAX_LENGTH_MEASURE,
                               MAX_LENGTH_RECIPE, MAX_LENGTH_SHORT_URL,
                               MAX_LENGTH_TAG, MAX_LENGTH_URL)

User = get_user_model()


class Tag(models.Model):
    name = models.CharField('Название', max_length=MAX_LENGTH_TAG,
                            unique=True)
    slug = models.SlugField('Слаг', max_length=MAX_LENGTH_TAG, unique=True,
                            blank=True, null=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField('Название',
                            max_length=MAX_LENGTH_INGREDIENT, db_index=True)
    measurement_unit = models.CharField('Единица измерения',
                                        max_length=MAX_LENGTH_MEASURE)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_Ingredient_unit'
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE,
                               related_name='recipe_ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField('Количество',
                                         validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Количество ингредиента в рецепте'
        verbose_name_plural = 'Количества ингредиентов в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            ),
        ]

    def __str__(self):
        return (f'"{self.recipe.name}" - {self.ingredient.name}: {self.amount}'
                f'{self.ingredient.measurement_unit}')


class BaseUserRecipeModel(models.Model):
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             related_name='%(class)s',
                             verbose_name='Пользователь',
                             db_index=True)
    recipe = models.ForeignKey('Recipe',
                               on_delete=models.CASCADE,
                               related_name='%(class)s_by',
                               verbose_name='Рецепт',
                               db_index=True)

    class Meta():
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_%(class)s_recipe'
            )
        ]
        indexes = [
            models.Index(
                fields=['user', 'recipe']
            )
        ]


class Favorite(BaseUserRecipeModel):

    class Meta(BaseUserRecipeModel.Meta):
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'

    def __str__(self):
        return (f'{self.user.username} → {self.recipe.name}')


class ShoppingCart(BaseUserRecipeModel):

    class Meta(BaseUserRecipeModel.Meta):
        verbose_name = 'Покупка'
        verbose_name_plural = 'Список покупок'

    def __str__(self):
        return (f'Список покупок {self.user.username}')


class Recipe(models.Model):
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               related_name='recipes',
                               verbose_name='Автор')
    name = models.CharField('Название', max_length=MAX_LENGTH_RECIPE)
    image = models.ImageField('Изображение', upload_to='recipes/',
                              null=True, blank=True)
    text = models.TextField('Описание')
    ingredients = models.ManyToManyField(Ingredient,
                                         through='RecipeIngredient',
                                         verbose_name='Ингредиенты')
    tags = models.ManyToManyField(Tag, blank=True,
                                  related_name='recipes',
                                  verbose_name='Теги')
    cooking_time = models.PositiveIntegerField(
        'Время приготовления (в минутах)', validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class ShortLink(models.Model):
    original_url = models.URLField(max_length=MAX_LENGTH_URL)
    short_code = models.CharField(max_length=MAX_LENGTH_SHORT_URL)
