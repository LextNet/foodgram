import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (Favourite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from serializers.users import UserProfileSerializer
from users.models import Subscribe

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('id', 'name', 'slug')
        model = Tag
        read_only_fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('id', 'name', 'measurement_unit')
        model = Ingredient


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True)

    class Meta:
        fields = ['id', 'name', 'measurement_unit', 'amount']
        model = RecipeIngredient


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Если это base64-строка с префиксом
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                # Разделяем формат и данные
                format, imgstr = data.split(';base64,')
                ext = format.split('/')[-1]
                # Декодируем base64
                decoded_file = base64.b64decode(imgstr)
                # Создаём ContentFile с именем
                data = ContentFile(decoded_file, name=f'temp.{ext}')
            except Exception as e:
                raise serializers.ValidationError(
                    f"Некорректный формат base64-изображения: {str(e)}"
                )
        # Для обычных файлов передаём дальше
        return super().to_internal_value(data)


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserProfileSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True, read_only=True
    )
    image = Base64ImageField(use_url=True)
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(read_only=True,
                                                   default=False)

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients', 'name', 'image',
            'text', 'cooking_time', 'is_in_shopping_cart', 'is_favorited'
        ]


class RecipeCreateSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True
    )
    image = Base64ImageField(use_url=True)
    is_favorited = serializers.BooleanField(read_only=True, default=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True,
                                                   default=True)

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'ingredients', 'name', 'image', 'text',
            'cooking_time', 'author', 'is_in_shopping_cart', 'is_favorited'
        ]

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Список ингредиентов не может быть пустым.")

        ingredient_ids = [item['ingredient'].id for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError("Повторяющиеся ингредиенты "
                                              "не допускаются.")
        errors = []
        for i, ingredient in enumerate(value):
            amount = ingredient.get('amount')
            if amount is None:
                errors.append({
                    'amount': 'Это поле является обязательным.'
                })
            elif amount <= 0:
                errors.append({
                    'amount': 'Количество ингредиента должно быть больше 0.'
                })
            else:
                errors.append({})

        if any(errors):
            raise serializers.ValidationError({'ingredients': errors})
        return value

    def validate_tags(self, value):
        # Проверка на пустой список тегов
        if not value:
            raise serializers.ValidationError("Список тегов не может"
                                              " быть пустым.")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Повторяющиеся теги"
                                              " не допускаются.")
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError({
                'image': 'Изображение обязательно для рецепта'
            })
        return value

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError("Время приготовления должно быть"
                                              " не менее 1 минуты.")
        return value

    def validate(self, data):
        if 'ingredients' not in self.initial_data:
            raise serializers.ValidationError({
                'ingredients': 'Необходимо указать ингредиенты.'
            })
        elif 'tags' not in self.initial_data:
            raise serializers.ValidationError({
                'tags': 'Необходимо указать tags.'
            })
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        tags_data = validated_data.pop('tags')
        author = self.context['request'].user

        validated_data.pop('author', None)
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags_data)

        # Создаём связи рецепт-ингредиент
        recipe_ingredients = []
        for item in ingredients_data:
            recipe_ingredients.append(
                RecipeIngredient(recipe=recipe,
                                 ingredient=item['ingredient'],
                                 amount=item['amount']))
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', None)
        tags_data = validated_data.pop('tags', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            # Удаляем старые связи
            instance.recipe_ingredients.all().delete()

            # Создаём новые связи
            recipe_ingredients = []
            for item in ingredients_data:
                recipe_ingredients.append(
                    RecipeIngredient(recipe=instance,
                                     ingredient=item['ingredient'],
                                     amount=item['amount']))
            RecipeIngredient.objects.bulk_create(recipe_ingredients)

        author = instance.author
        request = self.context.get('request')
        author.is_subscribed = Subscribe.objects.filter(
            subscriber=request.user,
            author=author).exists()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Заменяем ID тегов на объекты
        tags_queryset = instance.tags.all()
        data['tags'] = TagSerializer(tags_queryset, many=True).data
        return data


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = Base64ImageField(use_url=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavouriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favourite
        fields = ('id', 'recipe', 'user')


class ShoppingCartSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShoppingCart
        fields = ('id', 'user', 'recipe')


class SubscribedUserSerializer(serializers.ModelSerializer):

    is_subscribed = serializers.BooleanField(read_only=True)
    avatar = serializers.ImageField(read_only=True)
    recipes = RecipeMinifiedSerializer(source='limited_recipes',
                                       many=True, read_only=True)
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        ]
