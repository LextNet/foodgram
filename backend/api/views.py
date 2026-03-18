from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Count, Sum, Value
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters import rest_framework as django_filters
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, ShortLink, Tag)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomPageNumberPagination
from api.permissions import IsRecipeAuthor
from api.serializers.recipes import (FavoriteDeleteSerializer,
                                     FavoriteSerializer, IngredientSerializer,
                                     RecipeCreateSerializer,
                                     RecipeMinifiedSerializer,
                                     RecipeSerializer,
                                     ShoppingCartDeleteSerializer,
                                     ShoppingCartSerializer,
                                     SubscribedUserSerializer,
                                     SubscriptionActionSerializer,
                                     TagSerializer)
from api.serializers.users import AvatarUploadSerializer, UserProfileSerializer
from api.utils import generate_short_code_from_id

User = get_user_model()


class PublicUserViewSet(UserViewSet):
    serializer_class = UserProfileSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = User.objects.all()

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
        methods=['get'],
        url_path='me',
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """GET /api/users/me/ — профиль текущего пользователя"""
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated],
        serializer_class=AvatarUploadSerializer
    )
    def avatar(self, request):
        """
        PUT /api/users/me/avatar/ — загрузка аватара
        DELETE /api/users/me/avatar/ — удаление аватара
        """
        if request.method == 'PUT':
            serializer = self.get_serializer(
                request.user,
                data=request.data,
                partial=False
            )
            if not serializer.is_valid():
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer.save()
            avatar_url = serializer.data['avatar']
            return Response({'avatar': avatar_url}, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
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


class RecipeActionMixin:
    def _favorite_shoppingcart_action(self, request, pk, action_config):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            serializer = action_config['create_serializer'](
                data={'recipe': recipe.id, 'user': user.id},
                context={'request': request, 'view': self})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            recipe_serializer = RecipeMinifiedSerializer(
                recipe,
                context={'request': request})
            return Response(recipe_serializer.data,
                            status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            serializer = action_config['delete_serializer'](
                data={},
                context={'request': request, 'view': self})
            serializer.is_valid(raise_exception=True)
            deleted_count, _ = action_config['model'].objects.filter(
                user=user,
                recipe=recipe).delete()
            return Response(
                {'succes': action_config['success_message']},
                status=status.HTTP_204_NO_CONTENT
            )


class RecipeViewSet(RecipeActionMixin, viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = [IsRecipeAuthor]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = CustomPageNumberPagination
    ordering_fields = ['id', 'name']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        queryset = (
            Recipe.objects
            .select_related('author')
            .prefetch_related('recipe_ingredients__ingredient',
                              'favorite_by', 'shoppingcart_by')
        )
        return queryset

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
        short_link = f'{host}/api/s/{short_code}/'
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        config = {
            'model': Favorite,
            'success_message': 'Рецепт удалён из избранного',
            'create_serializer': FavoriteSerializer,
            'delete_serializer': FavoriteDeleteSerializer
        }
        return self._favorite_shoppingcart_action(request, pk, config)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        config = {
            'model': ShoppingCart,
            'success_message': 'Рецепт удален из списка покупок',
            'create_serializer': ShoppingCartSerializer,
            'delete_serializer': ShoppingCartDeleteSerializer
        }
        return self._favorite_shoppingcart_action(request, pk, config)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        user = request.user
        try:
            ingredients = RecipeIngredient.objects.filter(
                recipe__shoppingcart_by__user=user
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
                text += '- {}: ({}) — {}\n'.format(
                    item['ingredient__name'],
                    item['total_amount'],
                    item['ingredient__measurement_unit']
                )

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


class SubscriptionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = SubscribedUserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get']

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.filter(
            subscribers__subscriber=user
        ).annotate(
            is_subscribed=Value(True, output_field=BooleanField()),
            recipes_count=Count('recipes')
        ).prefetch_related('recipes')
        return queryset


class SubscriptionViewEdit(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def post(self, request, pk=None):
        """POST /api/users/{id}/subscribe/"""
        action_serializer = SubscriptionActionSerializer(
            data={},
            context={'request': request, 'view': self}
        )
        action_serializer.is_valid(raise_exception=True)
        author = action_serializer.save()
        annotated_author = User.objects.filter(pk=author.pk).annotate(
            is_subscribed=Value(True, output_field=BooleanField()),
            recipes_count=Count('recipes')
        ).first()
        serializer = SubscribedUserSerializer(annotated_author,
                                              context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk=None):
        """DELETE /api/users/{id}/subscribe/"""
        action_serializer = SubscriptionActionSerializer(
            data={},
            context={'request': request, 'view': self}
        )
        action_serializer.is_valid(raise_exception=True)
        action_serializer.destroy()
        return Response(status=status.HTTP_204_NO_CONTENT)


def redirect_short_link(request, short_code):
    short_link = get_object_or_404(ShortLink, short_code=short_code)
    return HttpResponseRedirect(short_link.original_url)
