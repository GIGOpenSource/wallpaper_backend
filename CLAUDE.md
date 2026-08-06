# WallPaper Django 项目指南

## 项目概述
- **框架**: Django 5.2.7 + Django REST Framework
- **数据库**: PostgreSQL (wallpaper_db)
- **配置文件**: `Wallpaper/settings/pro.py`
- **API文档**: drf-spectacular (Swagger UI: `/api/docs/`)

## 常用命令

### 迁移命令
```bash
python manage.py makemigrations models
python manage.py migrate models
```

### 运行项目
```bash
python manage.py runserver
```

## 项目结构

```
WallPaper/
├── App/                    # 应用目录
│   ├── urls.py             # 路由配置
│   └── view/               # 所有视图目录
│       ├── user/           # 用户相关视图
│       │   ├── view.py     # 视图函数
│       │   └── urls.py     # 子路由
│       ├── customer/       # 客户视图
│       ├── wallpapers/     # 壁纸视图
│       ├── notifications/  # 通知视图
│       ├── site/           # 站点配置视图
│       ├── dashboard/      # 仪表盘视图
│       ├── strategy/       # 策略视图
│       ├── operation_log/  # 操作日志视图
│       ├── seo/            # SEO视图
│       ├── track/          # 追踪视图
│       ├── page_stats/     # 页面统计视图
│       └── tasks/          # 任务视图
├── models/                 # 数据模型目录
│   ├── models.py           # 模型定义
│   └── migrations/         # 迁移文件
├── tool/                   # 工具目录
│   ├── utils.py            # ApiResponse、CustomPagination
│   ├── base_views.py       # BaseViewSet
│   ├── authentication.py   # 认证类
│   ├── permissions.py      # 权限类
│   └── token_tools.py      # Token工具
├── Wallpaper/              # 项目配置
│   ├── urls.py             # 主路由
│   └── settings/           # 配置目录
│       └── pro.py          # 生产配置
└── resource/               # 资源目录
    ├── font/               # 字体
    ├── image/              # 图片
    ├── sign/               # 签名
    ├── key/                # 密钥
    └── downloads/          # 下载
```

## 核心组件

### ApiResponse (tool/utils.py)
统一响应格式，所有视图使用此返回结果：

```python
from tool.utils import ApiResponse

# 成功响应
return ApiResponse(data={"key": "value"}, message="操作成功")

# 带状态码
return ApiResponse(code=201, data=serializer.data, message="创建成功")

# 错误响应
return ApiResponse(code=400, message="参数错误")
```

**响应格式**:
```json
{
    "code": 200,
    "message": "success",
    "data": {}
}
```

### CustomPagination (tool/utils.py)
分页器，前端参数：
- `currentPage`: 当前页码
- `pageSize`: 每页数量

```python
from tool.utils import CustomPagination

class MyViewSet(BaseViewSet):
    pagination_class = CustomPagination
```

### BaseViewSet (tool/base_views.py)
基础ViewSet，已实现通用的CRUD操作并返回ApiResponse格式：

```python
from tool.base_views import BaseViewSet

class MyViewSet(BaseViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer
    pagination_class = CustomPagination
```

## 国际化

### 配置
- 默认语言: `zh-hans` (简体中文)
- 时区: `Asia/Shanghai`
- 支持语言: 西班牙语、英语、葡萄牙语、日语、韩语、简体中文、繁体中文、德语、法语

### 使用方式
```python
from django.utils.translation import gettext as _

# 在视图中使用
return ApiResponse(message=_("操作成功"))

# 在序列化器验证中使用
raise serializers.ValidationError(_("两次输入的密码不一致"))
```

### 生成翻译文件
```bash
python manage.py makemessages -l en  # 英语
python manage.py makemessages -l ja  # 日语
python manage.py compilemessages     # 编译翻译文件
```

## 认证与权限

### 认证类 (tool/authentication.py)
- `TokenAuthentication`: Token认证，请求头携带 `token: <值>`
- `CustomBasicAuthentication`: Basic认证，用于Swagger UI

### 权限类 (tool/permissions.py)
- `IsTokenValid`: Token有效
- `IsAdmin`: 管理员权限
- `IsOwnerOrAdmin`: 所有者或管理员

### 视图权限配置示例
```python
class MyViewSet(viewsets.ViewSet):
    permission_classes_by_action = {
        'list': [IsTokenValid],
        'create': [IsAdmin],
        'destroy': [IsTokenValid, IsOwnerOrAdmin],
    }

    def get_permissions(self):
        return [perm() for perm in self.permission_classes_by_action.get(self.action, [])]
```

## 视图编写规范

### 使用ViewSet
```python
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view

from tool.base_views import BaseViewSet
from tool.utils import ApiResponse, CustomPagination
from django.utils.translation import gettext as _

@extend_schema(tags=["模块名称"])
@extend_schema_view(
    list=extend_schema(summary='获取列表'),
    create=extend_schema(summary='创建'),
)
class MyViewSet(BaseViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        # 自定义列表逻辑
        return ApiResponse(data=serializer.data)

    @action(detail=False, methods=['post'], url_path='custom-action')
    def custom_action(self, request):
        # 自定义action
        return ApiResponse(message=_("操作成功"))
```

### 路由配置 (urls.py)
```python
from rest_framework.routers import DefaultRouter
from .view import MyViewSet

router = DefaultRouter()
router.register(r'my-resource', MyViewSet, basename='my-resource')

urlpatterns = [
    path('', include(router.urls)),
]
```

## 日志配置

日志目录: `logs/` (按日期分目录)
- `info.log`: INFO级别日志
- `error.log`: ERROR级别日志

```python
import logging
logger = logging.getLogger(__name__)

logger.info("信息日志")
logger.error("错误日志")
```

## API文档

- Swagger UI: `GET /api/docs/`
- ReDoc: `GET /api/redoc/`
- Schema: `GET /api/schema/`

### 文档装饰器
```python
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

@extend_schema(tags=["模块名称"])
@extend_schema_view(
    list=extend_schema(
        summary='获取列表',
        parameters=[
            OpenApiParameter(name="keyword", type=str, required=False, description="搜索关键词"),
        ],
    ),
)
```

## 路由结构

所有API前缀: `/api/`

```
/api/                       # 用户相关 (user)
/api/client/                # 客户相关 (customer)
/api/wallpapers/            # 壁纸相关
/api/notifications/         # 通知相关
/api/site/                  # 站点配置
/api/dashboard/             # 仪表盘
/api/strategy/              # 策略
/api/operation_log/         # 操作日志
/api/seo/                   # SEO
/api/track/                 # 追踪
/api/page_stats/            # 页面统计
/api/tasks/                 # 任务
/api/docs/                  # Swagger文档
```

## 注意事项

1. **Django纯净版**: 已移除内置的token认证、路由跳转等
2. **迁移命令**: 只使用 `python manage.py makemigrations models` 和 `python manage.py migrate models`
3. **模型位置**: `models/models.py`
4. **视图位置**: `App/view/xxx/view.py`
5. **响应格式**: 统一使用 `ApiResponse` 返回
6. **国际化**: 使用 `_()` 函数包裹需要翻译的字符串
