from django.contrib.auth.models import User
from django.db import models


class BotUser(models.Model):
    user_id = models.BigIntegerField(unique=True)
    user_first_name = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.user_id} {self.user_first_name}'


class Skin(models.Model):
    # name = models.CharField(max_length=255)
    condition = models.CharField(max_length=255, null=True, blank=True)
    skin_id = models.CharField(max_length=255)
    skin_name = models.CharField(max_length=255)
    last_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    last_checked = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['skin_id', 'condition'], name='unique_skin_condition')
        ]

    def __str__(self):
        return f'{self.skin_id} {self.condition}'


class UserSkin(models.Model):
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE)
    skin = models.ForeignKey(Skin, on_delete=models.CASCADE, related_name="subscriptions")
    # notify_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    threshold_value = models.IntegerField(default=0)
    last_notified_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # 👈 добавь это
    class Meta:
        unique_together = ('user', 'skin')

    def __str__(self):
        return f'{self.user.user_id} {self.skin.skin_id}'
