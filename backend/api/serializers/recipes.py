from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from api.serializers.users import UserProfileSerializer
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
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


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserProfileSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True, read_only=True
    )
    image = Base64ImageField(use_url=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients', 'name', 'image',
            'text', 'cooking_time', 'is_in_shopping_cart', 'is_favorited'
        ]

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


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
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'ingredients', 'name', 'image', 'text',
            'cooking_time', 'author', 'is_in_shopping_cart', 'is_favorited'
        ]

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()

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


class FavoriteValidationMixin:
    def _get_user(self):
        return self.context['request'].user

    def _get_recipe(self):
        recipe_id = self.context['view'].kwargs.get('pk')
        return get_object_or_404(Recipe, pk=recipe_id)

    def _check_recipe_in_favorite(self, should_exist=True):
        user = self._get_user()
        recipe = self._get_recipe()
        recipe_exists = Favorite.objects.filter(user=user, recipe=recipe
                                                ).exists()
        if not should_exist and recipe_exists:
            raise serializers.ValidationError(
                {'error': 'Рецепт уже в избранном'}
            )
        elif should_exist and not recipe_exists:
            raise serializers.ValidationError(
                {'error': 'Рецепт не в избранном'}
            )
        return {'user': user, 'recipe': recipe}


class FavoriteSerializer(FavoriteValidationMixin,
                         serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = ('id', 'recipe', 'user')

    def validate(self, data):
        self._check_recipe_in_favorite(should_exist=False)
        return data


class FavoriteDeleteSerializer(FavoriteValidationMixin,
                               serializers.Serializer):
    def validate(self, data):
        self._check_recipe_in_favorite(should_exist=True)
        return data


class ShoppingCartValidationMixin:
    def _get_user(self):
        return self.context['request'].user

    def _get_recipe(self):
        recipe_id = self.context['view'].kwargs.get('pk')
        return get_object_or_404(Recipe, pk=recipe_id)

    def _check_recipe_in_cart(self, should_exist=True):
        user = self._get_user()
        recipe = self._get_recipe()
        recipe_exists = ShoppingCart.objects.filter(user=user, recipe=recipe
                                                    ).exists()
        if not should_exist and recipe_exists:
            raise serializers.ValidationError(
                {'error': 'Рецепт уже в списке покупок'}
            )
        elif should_exist and not recipe_exists:
            raise serializers.ValidationError(
                {'error': 'Рецепт не найден в списке покупок'}
            )
        return {'user': user, 'recipe': recipe}


class ShoppingCartSerializer(ShoppingCartValidationMixin,
                             serializers.ModelSerializer):

    class Meta:
        model = ShoppingCart
        fields = ('id', 'recipe', 'user')

    def validate(self, data):
        # Проверяем что рецепта НЕТ в корзине (для создания)
        self._check_recipe_in_cart(should_exist=False)
        return data


class ShoppingCartDeleteSerializer(ShoppingCartValidationMixin,
                                   serializers.Serializer):
    def validate(self, data):
        # Проверяем что рецепт ЕСТЬ в корзине (для удаления)
        self._check_recipe_in_cart(should_exist=True)
        return data


class SubscribedUserSerializer(serializers.ModelSerializer):

    is_subscribed = serializers.BooleanField(read_only=True)
    avatar = serializers.ImageField(read_only=True)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        ]

    def get_recipes(self, obj):
        recipes_limit = self.context['request'].query_params.get(
            'recipes_limit')
        try:
            recipes_limit = int(recipes_limit) if recipes_limit else None
        except (ValueError, TypeError):
            recipes_limit = None
        all_recipes = obj.recipes.order_by('-id')
        if recipes_limit:
            all_recipes = all_recipes[:recipes_limit]
        serializer = RecipeMinifiedSerializer(
            all_recipes,
            many=True,
            context={'request': self.context['request']}
        )
        return serializer.data


class SubscriptionActionSerializer(serializers.Serializer):

    def validate(self, data):
        request = self.context['request']
        author_id = self.context['view'].kwargs.get('pk')
        author = get_object_or_404(User, pk=author_id)
        subscriber = request.user

        if author == subscriber:
            raise serializers.ValidationError(
                {'error': 'Cannot subscribe to yourself'},
                code='self_subscription'
            )

        subscription_exists = Subscribe.objects.filter(
            author=author, subscriber=subscriber
        ).exists()

        if self.context['request'].method == 'POST':
            if subscription_exists:
                raise serializers.ValidationError(
                    {'error': 'Already subscribed to this user'},
                    code='already_subscribed'
                )
        elif self.context['request'].method == 'DELETE':
            if not subscription_exists:
                raise serializers.ValidationError(
                    {'error': 'Subscription does not exist'},
                    code='not_subscribed'
                )
        self.author = author
        self.subscriber = subscriber
        return data

    def create(self, validated_data):
        Subscribe.objects.create(
            author=self.author,
            subscriber=self.subscriber
        )
        return self.author

    def destroy(self):
        Subscribe.objects.filter(
            author=self.author,
            subscriber=self.subscriber
        ).delete()
        return self.author
