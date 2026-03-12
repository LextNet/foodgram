from django.contrib.auth import get_user_model
from django.db.models import (BooleanField, Count, Exists, OuterRef, Prefetch,
                              Sum, Value)
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters import rest_framework as django_filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomPageNumberPagination
from api.permissions import IsRecipeAuthor
from api.serializers.recipes import (IngredientSerializer,
                                     RecipeCreateSerializer,
                                     RecipeMinifiedSerializer,
                                     RecipeSerializer,
                                     SubscribedUserSerializer, TagSerializer)
from api.serializers.users import (AvatarUploadSerializer,
                                   PasswordChangeSerializer,
                                   UserProfileSerializer,
                                   UserRegistrationSerializer)
from api.utils import generate_short_code_from_id
from recipes.models import (Favourite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, ShortLink, Tag)
from users.models import Subscribe

User = get_user_model()


class PublicUserViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    http_method_names = ['get', 'post']
    pagination_class = CustomPageNumberPagination

    def create(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = User.objects.all()

        # Добавляем аннотацию is_subscribed для текущего пользователя
        user = self.request.user
        if user.is_authenticated:
            subscribed = Subscribe.objects.filter(
                author=OuterRef('pk'),
                subscriber=user
            )
            queryset = queryset.annotate(
                is_subscribed=Exists(subscribed)
            )
        else:
            # Для неавторизованных пользователей всегда False
            queryset = queryset.annotate(
                is_subscribed=Value(False, output_field=BooleanField()))

        request = self.request
        for obj in queryset:
            if obj.avatar:
                obj.avatar = request.build_absolute_uri(obj.avatar.url)
            else:
                obj.avatar = None

        queryset = queryset.exclude(is_superuser=True)
        return queryset

    @action(
        detail=False,
        methods=['post'],
        url_path='set_password'
    )
    def set_password(self, request):
        serializer = PasswordChangeSerializer(data=request.data,
                                              context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserProfileMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Аннотируем пользователя флагом подписки
        subscribed_subquery = Subscribe.objects.filter(
            author=OuterRef('pk'),
            subscriber=user
        )
        annotated_user = User.objects.annotate(
            is_subscribed=Exists(subscribed_subquery)
        ).get(pk=user.pk)
        serializer = UserProfileSerializer(
            annotated_user,
            context={'request': request}
        )
        avatar_url = None
        if annotated_user.avatar:
            if request:
                avatar_url = request.build_absolute_uri(
                    annotated_user.avatar.url)
            else:
                avatar_url = annotated_user.avatar.url

        # Добавляем URL аватара в ответ
        response_data = serializer.data
        response_data['avatar'] = avatar_url
        return Response(response_data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # PUT /users/me/avatar/
    # ------------------------------------------------------------------
    def put(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert Base64 string to ContentFile
        avatar_file = serializer.validated_data['avatar']

        # Save the file to the user instance
        user = request.user
        try:
            user.avatar.save(avatar_file.name, avatar_file, save=True)
        except Exception:
            return Response(
                {'error': 'Failed to save avatar'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        # Build absolute URL for the avatar
        avatar_url = request.build_absolute_uri(user.avatar.url)
        return Response({'avatar': avatar_url}, status=status.HTTP_200_OK)

    def delete(self, request):
        """Remove avatar"""
        user = request.user
        if user.avatar:
            user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = CustomPageNumberPagination
    ordering_fields = ['id', 'name']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'get_short_link',
                           'partial_update', 'destroy']:
            return [AllowAny(), IsRecipeAuthor()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Recipe.objects
            .select_related('author')
            .prefetch_related('recipe_ingredients__ingredient')
        )

        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    Favourite.objects.filter(user=user, recipe=OuterRef('pk'))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(user=user,
                                                recipe=OuterRef('pk'))
                )
            )
        else:
            # Для анонимных пользователей явно задаём False
            queryset = queryset.annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                is_in_shopping_cart=Value(False, output_field=BooleanField())
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_short_link(self, request, pk=None):
        recipe_detail_url = reverse('api:recipes-detail', kwargs={'pk': pk})
        result_detail_url = recipe_detail_url.replace("api/", "", 1)
        full_url = request.build_absolute_uri(result_detail_url)
        short_code = generate_short_code_from_id(pk)

        short_link, created = ShortLink.objects.get_or_create(
            original_url=full_url,
            short_code=short_code
        )
        if not created:
            short_code = short_link.short_code
        host = request.get_host()
        # protocol = 'https' if request.is_secure() else 'http'
        # short_link = f"{protocol}://{host}/api/s/{short_code}/"
        short_link = f'{host}/api/s/{short_code}/'
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """
        POST /api/recipes/{id}/favorite/
        Добавить рецепт в избранное.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            # Проверяем, что рецепт ещё не в избранном
            if Favourite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'error': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favourite.objects.create(user=user, recipe=recipe)
            serializer = RecipeMinifiedSerializer(recipe,
                                                  context={'request': request})
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            deleted_count, _ = Favourite.objects.filter(user=user,
                                                        recipe=recipe).delete()
            if deleted_count == 0:
                return Response(
                    {'error': 'Рецепт не в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'succes': 'Рецепт удален из избранного'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        try:
            ingredients = RecipeIngredient.objects.filter(
                recipe__shoppingcart__user=user
            ).values(
                'ingredient__name', 'ingredient__measurement_unit').annotate(
                total_amount=Sum('amount')).order_by('ingredient__name')

            if not ingredients.exists():
                response = HttpResponse('Ваш список покупок пуст.',
                                        content_type='text/plain;'
                                        ' charset=utf-8')
                response['Content-Disposition'] = (
                    'attachment; filename="shopping_cart.txt"')
                return response

            text = f'Список покупок для {user.username}: \n\n'
            for item in ingredients:
                text += (f'- {item['ingredient__name']}: '
                         f'({item['total_amount']}) — '
                         f'{item['ingredient__measurement_unit']}\n')

            response = HttpResponse(text, content_type='text/plain;'
                                    ' charset=utf-8')
            response['Content-Disposition'] = (
                'attachment; filename="shopping_cart.txt"'
            )
            return response

        except Exception:
            return Response({'error': 'Произошла ошибка при формировании'
                            ' списка покупок'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'error': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(recipe=recipe, user=user)
            serializer = RecipeMinifiedSerializer(recipe,
                                                  context={'request': request})
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            deleted_count, _ = ShoppingCart.objects.filter(
                user=user,
                recipe=recipe).delete()
            if deleted_count == 0:
                return Response(
                    {'error': 'Рецепт не найден в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response({'success': 'Рецепт удален из списка покупок'},
                            status=status.HTTP_204_NO_CONTENT)


class SubscriptionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = SubscribedUserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get']

    def get_queryset(self):
        user = self.request.user
        recipes_limit = self.request.query_params.get('recipes_limit')
        try:
            recipes_limit = int(recipes_limit) if recipes_limit else None
        except (ValueError, TypeError):
            recipes_limit = None
        recipes_qs = Recipe.objects.order_by('-id')
        if recipes_limit:
            recipes_qs = recipes_qs[:recipes_limit]

        queryset = User.objects.filter(
            subscribers__subscriber=user).annotate(
                is_subscribed=Value(True, output_field=BooleanField()),
                recipes_count=Count('recipes'),).prefetch_related(
                Prefetch('recipes', queryset=recipes_qs,
                         to_attr='limited_recipes')
        )
        return queryset


class SubscriptionViewEdit(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def post(self, request, pk=None):
        """POST /api/users/{id}/subscribe/"""
        author = get_object_or_404(User, pk=pk)
        subscriber = request.user

        if author == subscriber:
            return Response(
                {'error': 'Cannot subscribe to yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if Subscribe.objects.filter(author=author, subscriber=subscriber
                                    ).exists():
            return Response(
                {'error': 'Already subscribed to this user'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Subscribe.objects.create(author=author, subscriber=subscriber)
        recipes_limit = request.query_params.get('recipes_limit')
        try:
            recipes_limit = int(recipes_limit) if recipes_limit else None
        except ValueError:
            recipes_limit = None

        recipes_qs = author.recipes.order_by('-id')
        if recipes_limit is not None:
            recipes_qs = recipes_qs[:recipes_limit]

        author = (
            User.objects.filter(pk=author.pk)
            .annotate(
                is_subscribed=Value(True, output_field=BooleanField()),
                recipes_count=Count('recipes')
            )
            .prefetch_related(
                Prefetch('recipes', queryset=recipes_qs,
                         to_attr='limited_recipes')
            )
            .first()
        )

        serializer = SubscribedUserSerializer(author,
                                              context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk=None):
        """DELETE /api/users/{id}/subscribe/"""
        author = get_object_or_404(User, pk=pk)
        subscriber = request.user

        subscription_exists = Subscribe.objects.filter(
            author=author,
            subscriber=subscriber
        ).exists()

        if not subscription_exists:
            return Response(
                {'error': 'Subscription does not exist'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Subscribe.objects.filter(author=author, subscriber=subscriber).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def redirect_short_link(request, short_code):
    short_link = get_object_or_404(ShortLink, short_code=short_code)
    return HttpResponseRedirect(short_link.original_url)
