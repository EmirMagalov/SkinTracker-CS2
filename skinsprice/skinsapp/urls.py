from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet,  UserSkinViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
# router.register(r'skins', SkinViewSet, basename='skin')
router.register(r'user-skins', UserSkinViewSet, basename='user-skin')

urlpatterns = [
    path('api/', include(router.urls)),
]