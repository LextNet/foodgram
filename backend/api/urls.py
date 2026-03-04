from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter, SimpleRouter

from api.views import (IngredientViewSet, PublicUserViewSet, RecipeViewSet,
                       SubscriptionViewEdit, SubscriptionViewSet, TagViewSet,
                       UserProfileMeView)

app_name = 'api'

Router = DefaultRouter if settings.DEBUG else SimpleRouter

router = Router()

router.register('users', PublicUserViewSet, basename='users')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')


urlpatterns = [
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('users/me/', UserProfileMeView.as_view(), name='user-me'),
    path('users/me/avatar/', UserProfileMeView.as_view(), name='user-avatar'),
    path('users/<int:pk>/subscribe/', SubscriptionViewEdit.as_view(),
         name='user-subscribe'),
    path('users/subscriptions/', SubscriptionViewSet.as_view({'get': 'list'}),
         name='subscriptions-list'),
    path('', include(router.urls)),
]
