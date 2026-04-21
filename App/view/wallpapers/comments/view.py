#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/4/15
@description : 壁纸评论功能
"""
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action
from django.db.models import F

from models.models import WallpaperComment, Wallpapers, Notification, WallpaperCommentLike
from tool.base_views import BaseViewSet
from tool.permissions import IsCustomerTokenValid, IsAdmin
from tool.token_tools import CustomTokenTool
from tool.utils import ApiResponse, CustomPagination
from tool.middleware import logger
from django.utils.translation import gettext as _


class WallpaperCommentSerializer(serializers.ModelSerializer):
    """壁纸评论序列化器"""
    customer_info = serializers.SerializerMethodField()
    parent_comment = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()


    class Meta:
        model = WallpaperComment
        fields = [
            'id', 'customer_info', 'wallpaper', 'parent', 'parent_comment',
            'content', 'like_count', 'is_hidden', 'replies_count', 'is_liked',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_info', 'like_count', 'created_at', 'updated_at', 'replies_count', 'is_liked']



    def get_customer_info(self, obj):
        """获取评论用户信息"""
        return {
            'id': obj.customer.id,
            'email': obj.customer.email,
            'nickname': obj.customer.nickname,
            'avatar_url': obj.customer.avatar_url,
        }
    
    def get_parent_comment(self, obj):
        """获取父评论信息（用于回复展示）"""
        if obj.parent:
            return {
                'id': obj.parent.id,
                'customer_name': obj.parent.customer.nickname or obj.parent.customer.email,
                'content': obj.parent.content[:50] + '...' if len(obj.parent.content) > 50 else obj.parent.content,
                'customer_avatar_url': obj.parent.customer.avatar_url,
            }
        return None
    
    def get_replies_count(self, obj):
        """获取回复数量"""
        if hasattr(obj, '_replies_count'):
            return obj._replies_count
        return obj.replies.count()

    def get_is_liked(self, obj):
        """判断当前用户是否点赞了该评论（直接查询数据库）"""
        customer_id = self.context.get('customer_id')
        if not customer_id:
            return False
        # 查询当前用户(customer_id)是否点赞了当前评论(obj.id)
        return WallpaperCommentLike.objects.filter(customer_id=customer_id, comment_id=obj.id).exists()


class WallpaperCommentAdminSerializer(serializers.ModelSerializer):
    """壁纸评论序列化器（管理员使用，不包含 is_liked）"""
    customer_info = serializers.SerializerMethodField()
    parent_comment = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    wallpaper_object = serializers.SerializerMethodField()

    class Meta:
        model = WallpaperComment
        fields = [
            'id', 'customer_info', 'wallpaper', 'parent', 'parent_comment',
            'content', 'like_count', 'is_hidden', 'replies_count',
            'created_at', 'updated_at','wallpaper_object'
        ]
        read_only_fields = ['id', 'customer_info', 'like_count', 'created_at', 'updated_at', 'replies_count']

    def get_wallpaper_object(self, obj):
        """获取壁纸信息"""
        return {
            'id': obj.wallpaper.id,
            'title': obj.wallpaper.title,
            'url': obj.wallpaper.url,
            'thumbnail_url': obj.wallpaper.thumbnail_url,
            'category': obj.wallpaper.category,
            'resolution': obj.wallpaper.resolution,
            'size': obj.wallpaper.size,
            'created_at': obj.wallpaper.created_at,
        }
    def get_customer_info(self, obj):
        """获取评论用户信息"""
        return {
            'id': obj.customer.id,
            'email': obj.customer.email,
            'nickname': obj.customer.nickname,
            'avatar_url': obj.customer.avatar_url,
        }

    def get_parent_comment(self, obj):
        """获取父评论信息"""
        if obj.parent:
            return {
                'id': obj.parent.id,
                'customer_name': obj.parent.customer.nickname or obj.parent.customer.email,
                'content': obj.parent.content[:50] + '...' if len(obj.parent.content) > 50 else obj.parent.content,
                'customer_avatar_url': obj.parent.customer.avatar_url,
            }
        return None

    def get_replies_count(self, obj):
        """获取回复数量"""
        if hasattr(obj, '_replies_count'):
            return obj._replies_count
        return obj.replies.count()

@extend_schema(tags=["壁纸评论"])
@extend_schema_view(
    list=extend_schema(
        summary="获取所有壁纸评论列表",
        description="获取指定壁纸的一级评论列表（支持分页）",
        parameters=[
            OpenApiParameter(name="wallpaper_id", type=int, required=False, description="壁纸ID"),
            OpenApiParameter(name="currentPage", type=int, required=False, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, description="每页数量"),
            OpenApiParameter(name="is_hidden", type=bool, required=False, description="按隐藏状态筛选"),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 200},
                    "data": {
                        "type": "object",
                        "properties": {
                            "results": {"type": "array", "items": {"$ref": "#/components/schemas/WallpaperComment"}},
                            "total": {"type": "integer", "example": 50},
                            "pagination": {
                                "type": "object",
                                "properties": {
                                    "page": {"type": "integer"},
                                    "page_size": {"type": "integer"},
                                    "total": {"type": "integer"},
                                    "total_pages": {"type": "integer"}
                                }
                            }
                        }
                    },
                    "message": {"type": "string", "example": "评论列表获取成功"}
                }
            }
        }
    ),
    create=extend_schema(
        summary="发表评论",
        description="对指定壁纸发表评论，可选回复某条评论",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "wallpaper_id": {"type": "integer", "description": "壁纸ID（评论壁纸时必填）"},
                    "parent_id": {"type": "integer", "description": "父评论ID（回复评论时必填）"},
                    "content": {"type": "string", "description": "评论内容"}
                },
                "required": ["content"]
            }
        },
        responses={201: WallpaperCommentSerializer}
    ),
    retrieve=extend_schema(summary="获取评论详情", responses={200: WallpaperCommentSerializer, 404: "评论不存在"}),
    update=extend_schema(
        summary="更新评论",
        description="修改自己的评论内容",
    ),
    partial_update=extend_schema(
        summary="部分更新评论",
        description="部分修改自己的评论内容",
    ),
    destroy=extend_schema(
        summary="删除评论",
        description="删除自己的评论",
        responses={204: "删除成功", 404: "评论不存在"}
    )
)
class WallpaperCommentViewSet(BaseViewSet):
    """
    壁纸评论 ViewSet
    提供评论的增删改查及回复功能
    """
    queryset = WallpaperComment.objects.all()
    serializer_class = WallpaperCommentSerializer
    pagination_class = CustomPagination
    permission_classes = []

    def get_permissions(self):
        """根据不同操作返回不同的权限类"""
        if self.action == 'list':
            # list 方法需要管理员权限
            return [IsAdmin()]
        # 其他操作保持原有权限（公开）
        return []

    def get_serializer_class(self):
        """根据动作返回不同的序列化器"""
        if self.action == 'list':
            return WallpaperCommentAdminSerializer
        return WallpaperCommentSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        tok = self.request.headers.get("token")
        if tok:
            ok, cid = CustomTokenTool.verify_customer_token(tok)
            if ok:
                ctx["customer_id"] = cid
        return ctx

    def list(self, request, *args, **kwargs):
        """
        管理员获取所有评论列表
        """
        queryset = self.filter_queryset(self.get_queryset())
        # 支持按壁纸ID筛选
        wallpaper_id = request.query_params.get('wallpaper_id')
        if wallpaper_id:
            try:
                queryset = queryset.filter(wallpaper_id=int(wallpaper_id))
            except (ValueError, TypeError):
                pass
        # 支持按隐藏状态筛选
        is_hidden = request.query_params.get('is_hidden')
        if is_hidden is not None:
            if is_hidden.lower() == 'true':
                queryset = queryset.filter(is_hidden=True)
            elif is_hidden.lower() == 'false':
                queryset = queryset.filter(is_hidden=False)
        # 按时间倒序
        queryset = queryset.order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="评论列表获取成功")


    @extend_schema(
        summary="获取壁纸的评论列表",
        description="获取指定壁纸的一级评论列表（支持分页，无需登录）",
        parameters=[
            OpenApiParameter(name="wallpaper_id", type=int, required=False, location=OpenApiParameter.QUERY, description="壁纸ID"),
            OpenApiParameter(name="currentPage", type=int, required=False, location=OpenApiParameter.QUERY, description="当前页码"),
            OpenApiParameter(name="pageSize", type=int, required=False, location=OpenApiParameter.QUERY, description="每页数量"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='list')
    def list_comments(self, request):
        """获取壁纸评论列表（只显示一级评论，按时间倒序，每页20条）"""
        wallpaper_id = request.query_params.get('wallpaper_id')
        if not wallpaper_id:
            return ApiResponse(code=400, message="请提供 wallpaper_id")
        try:
            wallpaper_id = int(wallpaper_id)
        except (TypeError, ValueError):
            return ApiResponse(code=400, message="wallpaper_id 无效")
        # 只查询一级评论（parent 为 null），按创建时间倒序
        queryset = WallpaperComment.objects.filter(
            wallpaper_id=wallpaper_id,
            parent__isnull=True,
            is_hidden=False
        ).select_related('customer').order_by('-created_at')
        # 获取当前用户点赞的评论 ID 集合（仅针对当前壁纸下的评论）
        customer_id = self.get_serializer_context().get('customer_id')
        liked_comment_ids = set()
        if customer_id:
            # 1. 获取当前筛选条件下所有评论的 ID（不分页，为了准确匹配点赞状态）
            all_comment_ids = list(
                WallpaperComment.objects.filter(
                    wallpaper_id=wallpaper_id,
                    parent__isnull=True,
                    is_hidden=False
                ).values_list('id', flat=True)
            )
            
            if all_comment_ids:
                # 2. 查询这些评论中，哪些被当前用户点赞过
                liked_comment_ids = set(
                    WallpaperCommentLike.objects.filter(
                        customer_id=customer_id,
                        comment_id__in=all_comment_ids
                    ).values_list('comment_id', flat=True)
                )
                logger.info(f"用户 {customer_id} 在壁纸 {wallpaper_id} 下点赞了评论: {liked_comment_ids}")
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            context = self.get_serializer_context()
            context['liked_comment_ids'] = liked_comment_ids
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        
        context = self.get_serializer_context()
        context['liked_comment_ids'] = liked_comment_ids
        serializer = self.get_serializer(queryset, many=True, context=context)
        return ApiResponse(data=serializer.data, message="评论列表获取成功")
    
    def create(self, request, *args, **kwargs):
        """创建评论或回复
        
        支持三种情况：
        1. 评论壁纸：传 wallpaper_id + content
        2. 回复评论：传 parent_id + content（自动从父评论获取 wallpaper_id）
        3. 评论壁纸：传 wallpaper_id + content + parent_id=None
        """
        wallpaper_id = request.data.get('wallpaper_id')
        parent_id = request.data.get('parent_id')
        content = request.data.get('content', '').strip()
        
        # 参数校验
        if not content:
            return ApiResponse(code=400, message="评论内容不能为空")
        
        if len(content) > 1000:
            return ApiResponse(code=400, message="评论内容不能超过1000字")
        
        # 获取用户ID
        customer_id = self.get_serializer_context().get('customer_id')
        if not customer_id:
            return ApiResponse(code=401, message="请先登录")
        
        wallpaper = None
        parent_comment = None
        
        # 情况3：回复评论（只传 parent_id）
        if parent_id and not wallpaper_id:
            try:
                parent_id = int(parent_id)
                parent_comment = WallpaperComment.objects.get(id=parent_id)
                wallpaper_id = parent_comment.wallpaper_id
                wallpaper = parent_comment.wallpaper
            except (TypeError, ValueError):
                return ApiResponse(code=400, message="父评论ID无效")
            except WallpaperComment.DoesNotExist:
                return ApiResponse(code=404, message="父评论不存在")
        
        # 情况1和2：评论壁纸（传了 wallpaper_id）
        if wallpaper_id:
            try:
                wallpaper_id = int(wallpaper_id)
                wallpaper = Wallpapers.objects.get(id=wallpaper_id)
            except (TypeError, ValueError):
                return ApiResponse(code=400, message="wallpaper_id 无效")
            except Wallpapers.DoesNotExist:
                return ApiResponse(code=404, message="壁纸不存在")
            
            # 验证父评论属于该壁纸
            if parent_id and parent_comment:
                if parent_comment.wallpaper_id != wallpaper_id:
                    return ApiResponse(code=400, message="父评论不属于该壁纸")
        
        if not wallpaper:
            return ApiResponse(code=400, message="请提供 wallpaper_id 或 parent_id")
        
        # 创建评论
        try:
            comment = WallpaperComment.objects.create(
                customer_id=customer_id,
                wallpaper=wallpaper,
                parent=parent_comment,
                content=content
            )
            
            # 发送通知（使用统一通知中心）
            try:
                from App.view.notifications.notification_center import NotificationCenter
                
                # 1. 如果是回复评论，通知被回复者
                if parent_comment and parent_comment.customer_id != customer_id:
                    NotificationCenter.send_reply(
                        recipient_id=parent_comment.customer_id,
                        sender_id=customer_id,
                        comment_id=comment.id,
                        wallpaper_name=wallpaper.name[:50],
                        reply_content=content
                    )
                else:
                    # 2. 否则通知壁纸上传者（如果不是自己上传的）
                    upload_record = getattr(wallpaper, 'customer_upload', None)
                    if upload_record and upload_record.customer_id != customer_id:
                        NotificationCenter.send_comment(
                            recipient_id=upload_record.customer_id,
                            sender_id=customer_id,
                            wallpaper_id=wallpaper.id,
                            wallpaper_name=wallpaper.name[:50],
                            comment_content=content
                        )
            except Exception:
                pass
            
            serializer = self.get_serializer(comment)
            return ApiResponse(data=serializer.data, message="评论成功", code=201)
        except Exception as e:
            logger.error(f"创建评论失败：{str(e)}", exc_info=True)
            return ApiResponse(code=500, message=f"评论失败：{str(e)}")
    
    def update(self, request, *args, **kwargs):
        """更新评论"""
        instance = self.get_object()
        
        # 验证是否是自己的评论
        customer_id = self.get_serializer_context().get('customer_id')
        if instance.customer_id != customer_id:
            return ApiResponse(code=403, message="只能修改自己的评论")
        
        content = request.data.get('content', '').strip()
        if not content:
            return ApiResponse(code=400, message="评论内容不能为空")
        
        if len(content) > 1000:
            return ApiResponse(code=400, message="评论内容不能超过1000字")
        
        instance.content = content
        instance.save()
        
        serializer = self.get_serializer(instance)
        return ApiResponse(data=serializer.data, message="修改成功")
    
    def destroy(self, request, *args, **kwargs):
        """删除评论"""
        instance = self.get_object()
        # 验证是否是自己的评论
        customer_id = self.get_serializer_context().get('customer_id')
        is_owner = customer_id and instance.customer_id == int(customer_id)
        # 2) 管理员删除（后台权限最高）
        is_admin = IsAdmin().has_permission(request, self)
        if not (is_owner or is_admin):
            return ApiResponse(code=403, message="只能删除自己的评论或由管理员删除")

        instance.delete()
        return ApiResponse(message="删除成功")
    
    @extend_schema(summary="点赞/取消点赞评论")
    @action(detail=True, methods=['post'], url_path='toggle-like',permission_classes=[IsCustomerTokenValid])
    def toggle_like(self, request, pk=None):
        """点赞/取消点赞评论"""
        comment = self.get_object()
        customer_id = self.get_serializer_context().get('customer_id')
        
        try:
            # 尝试获取点赞记录
            like_record = WallpaperCommentLike.objects.filter(
                customer_id=customer_id, 
                comment=comment
            ).first()
            
            if like_record:
                # 取消点赞
                like_record.delete()
                # 简单递减，确保不为负数
                if comment.like_count > 0:
                    comment.like_count -= 1
                    comment.save(update_fields=['like_count'])
                liked_status = False
                message = "取消点赞"
            else:
                # 点赞
                WallpaperCommentLike.objects.create(
                    customer_id=customer_id,
                    comment=comment
                )
                comment.like_count = F('like_count') + 1
                comment.save(update_fields=['like_count'])
                comment.refresh_from_db(fields=['like_count'])
                liked_status = True
                message = "点赞成功"
                
                # 发送点赞通知（如果不是给自己点赞）
                try:
                    from App.view.notifications.notification_center import NotificationCenter
                    if comment.customer_id != customer_id:
                        NotificationCenter.send(
                            recipient_id=comment.customer_id,
                            notification_type='like',
                            content=f"赞了你的评论",
                            sender_id=customer_id,
                            target_id=comment.id,
                            target_type='comment',
                            extra_data={'wallpaper_name': comment.wallpaper.name[:50]}
                        )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"评论点赞失败：{str(e)}", exc_info=True)
            return ApiResponse(code=500, message="操作失败")
            
        return ApiResponse(
            data={'liked': liked_status, 'like_count': comment.like_count},
            message=message
        )
    
    @action(detail=False, methods=['get'], url_path='replies')
    def get_replies(self, request):
        """获取评论的回复列表"""
        comment_id = request.query_params.get('comment_id')
        if not comment_id:
            return ApiResponse(code=400, message="请提供 comment_id")
        
        try:
            comment_id = int(comment_id)
        except (TypeError, ValueError):
            return ApiResponse(code=400, message="comment_id 无效")
        
        queryset = WallpaperComment.objects.filter(
            parent_id=comment_id,
            is_hidden=False
        ).select_related('customer').order_by('created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="回复列表获取成功")
