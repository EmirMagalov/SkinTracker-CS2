from rest_framework import viewsets
from rest_framework.decorators import action
from .models import Skin, UserSkin, BotUser
from .serializers import BotUserSerializer, SkinSerializer, UserSkinSerializer
from rest_framework.response import Response


# Создание и просмотр пользователей

class UserViewSet(viewsets.ModelViewSet):
    queryset = BotUser.objects.all()
    serializer_class = BotUserSerializer


# Скины
# class SkinViewSet(viewsets.ModelViewSet):
#     queryset = Skin.objects.all()
#     serializer_class = SkinSerializer


# Подписки пользователей на скины
class UserSkinViewSet(viewsets.ModelViewSet):
    queryset = UserSkin.objects.all()
    serializer_class = UserSkinSerializer

    @action(methods=["post"], detail=False)
    def add_user_skin(self, request):
        user_id = request.data.get("user_id")
        skin_id = request.data.get('skin_id')
        skin_name = request.data.get('skin_name')
        last_price = request.data.get('last_price')
        condition = request.data.get('condition')
        skin, create = Skin.objects.get_or_create(skin_id=skin_id, skin_name=skin_name, condition=condition,
                                                  last_price=last_price)
        if last_price is not None:
            skin.last_price = last_price
            skin.save()
        user = BotUser.objects.get(user_id=user_id)

        user_skin, create = UserSkin.objects.get_or_create(user=user, skin=skin)
        serializer = UserSkinSerializer(user_skin)
        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def get_user_skin(self, request):
        user_id = request.query_params.get("user_id")
        skin_id = request.query_params.get('skin_id')
        condition = request.query_params.get('condition')
        if not condition or condition.lower() == 'none':
            condition = None
        user = BotUser.objects.get(user_id=user_id)
        try:
            if condition is None:
                skin = Skin.objects.get(skin_id=skin_id, condition__isnull=True)

            else:
                skin = Skin.objects.get(skin_id=skin_id, condition=condition)
        except Skin.DoesNotExist:
            return Response({"error": "Скин не найден"}, status=404)
        try:
            user_skin = UserSkin.objects.get(user=user, skin=skin)
        except UserSkin.DoesNotExist:
            return Response({"error": "Скин не найден"}, status=404)
        serializer = UserSkinSerializer(user_skin)
        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def get_user_skins(self, request):
        user_id = request.query_params.get("user_id")
        user = BotUser.objects.get(user_id=user_id)
        user_skins = UserSkin.objects.filter(user=user).select_related('skin').order_by('-id')
        serializer = UserSkinSerializer(user_skins, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False)
    def user_skin_trigger(self, request):
        user_id = request.data.get("user_id")
        skin_id = request.data.get('skin_id')
        condition = request.data.get('condition')
        threshold_value = request.data.get('threshold_value')
        last_price = request.data.get('last_price')

        # Приводим строку "None" или пустую строку к настоящему None
        if not condition or condition.lower() == 'none':
            condition = None

        user = BotUser.objects.get(user_id=user_id)

        if condition is None:
            skin = Skin.objects.get(skin_id=skin_id, condition__isnull=True)
        else:
            skin = Skin.objects.get(skin_id=skin_id, condition=condition)

        user_skin = UserSkin.objects.get(user=user, skin=skin)
        user_skin.threshold_value = threshold_value
        user_skin.last_notified_price = last_price
        user_skin.save()
        return Response({"success": True, "user_skin_id": user_skin.id})

    @action(methods=['delete'], detail=False)
    def delete_user_skin(self, request):
        user_id = request.query_params.get("user_id")
        skin_id = request.query_params.get('skin_id')
        condition = request.query_params.get('condition')

        # Приводим строку "None" или пустую строку к настоящему None
        if not condition or condition.lower() == 'none':
            condition = None

        user = BotUser.objects.get(user_id=user_id)

        if condition is None:
            skin = Skin.objects.get(skin_id=skin_id, condition__isnull=True)
        else:
            skin = Skin.objects.get(skin_id=skin_id, condition=condition)

        user_skin = UserSkin.objects.get(user=user, skin=skin)
        user_skin.delete()
        return Response({"success": True, "user_skin_id": user_skin.id})
