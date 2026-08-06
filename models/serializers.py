from rest_framework import serializers
from .models import Medal, UserMedal
from django.contrib.auth import get_user_model

class MedalSerializer(serializers.ModelSerializer):
    """勋章模板序列化器"""
    class Meta:
        model = Medal
        fields = ["id", "name", "level", "desc"]


class UserMedalSerializer(serializers.ModelSerializer):
    """用户拥有的勋章，嵌套勋章详情"""
    medal = MedalSerializer(read_only=True)

    class Meta:
        model = UserMedal
        fields = ["id", "medal", "create_time"]