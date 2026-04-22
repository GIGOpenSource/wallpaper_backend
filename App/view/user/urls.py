"""
@Project ：NoBad 
@File    ：urls.py
@Author  ：LYP
@Date    ：2025/10/30 13:26 
@description :
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.user.view import UserViewSet, RoleViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')  # 添加 basename 参数
router.register(r'roles', RoleViewSet, basename='role')  # 添加 basename 参数

urlpatterns = [
    path('', include(router.urls)),
]
