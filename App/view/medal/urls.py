from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.medal.view import MedalViewSet, MedalAdminViewSet, UserMedalViewSet

router = DefaultRouter()

# 公开接口
router.register(r'medals', MedalViewSet, basename='medal')

# 管理接口
router.register(r'admin/medals', MedalAdminViewSet, basename='medal-admin')

# 用户个人勋章
router.register(r'user/medals', UserMedalViewSet, basename='user-medal')

urlpatterns = [
    path('api/', include(router.urls)),
]