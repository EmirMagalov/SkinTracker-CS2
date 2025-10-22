from rest_framework import serializers

from .models import Skin, UserSkin, BotUser


class BotUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotUser
        fields = '__all__'


class SkinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skin
        fields = '__all__'


# Подписка пользователя на скин
class UserSkinSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=BotUser.objects.all())
    skin = serializers.PrimaryKeyRelatedField(queryset=Skin.objects.all())
    skin_id = serializers.CharField(source='skin.skin_id', read_only=True)
    condition = serializers.CharField(source='skin.condition', read_only=True)

    class Meta:
        model = UserSkin
        fields = ('id', 'user', 'skin', 'skin_id', 'threshold_value', 'condition', 'last_notified_price')
