#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：notification_center.py
@Author  ：Liang
@Date    ：2026/4/15
@description : 统一通知中心工具类
"""
from models.models import Notification, CustomerUser


class NotificationCenter:
    """
    统一通知发送中心
    用法：NotificationCenter.send(recipient_id, type, content, **kwargs)
    """

    @staticmethod
    def send(recipient_id, notification_type, content, sender_id=None, target_id=None, target_type=None, extra_data=None):
        """
        发送通知
        
        :param recipient_id: 接收者用户ID
        :param notification_type: 通知类型 (like, comment, reply, follow, reward, announcement)
        :param content: 通知内容文本
        :param sender_id: 发送者用户ID (系统通知可不传)
        :param target_id: 关联对象ID (如壁纸ID、评论ID)
        :param target_type: 关联对象类型 (wallpaper, comment, user等)
        :param extra_data: 额外扩展数据 (dict)
        :return: Notification 实例
        """
        if not recipient_id:
            return None

        # 确保接收者存在
        try:
            recipient = CustomerUser.objects.get(id=recipient_id)
        except CustomerUser.DoesNotExist:
            return None

        # 构建发送者对象（如果是系统通知，sender_id 可能为空）
        sender = None
        if sender_id:
            try:
                sender = CustomerUser.objects.get(id=sender_id)
            except CustomerUser.DoesNotExist:
                pass

        if not sender and notification_type not in ['reward', 'announcement']:
            # 非系统通知必须有发送者
            return None

        notification = Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            target_id=target_id,
            target_type=target_type,
            extra_data=extra_data or {},
            is_read=False
        )
        
        # 可以在这里添加 Redis 缓存更新逻辑，例如增加未读数
        # from django.core.cache import cache
        # cache.incr(f"unread_notifications_{recipient_id}")
        return notification

    @classmethod
    def send_like(cls, recipient_id, sender_id, wallpaper_id, wallpaper_name):
        """点赞通知"""
        return cls.send(
            recipient_id=recipient_id,
            notification_type='like',
            content=f"赞了你的帖子",
            sender_id=sender_id,
            target_id=wallpaper_id,
            target_type='wallpaper',
            extra_data={'wallpaper_name': wallpaper_name}
        )

    @classmethod
    def send_comment(cls, recipient_id, sender_id, wallpaper_id, wallpaper_name, comment_content):
        """评论通知"""
        return cls.send(
            recipient_id=recipient_id,
            notification_type='comment',
            content=f"评论了你的帖子",
            sender_id=sender_id,
            target_id=wallpaper_id,
            target_type='wallpaper',
            extra_data={
                'wallpaper_name': wallpaper_name,
                'comment_content': comment_content[:50]
            }
        )

    @classmethod
    def send_reply(cls, recipient_id, sender_id, comment_id, wallpaper_name, reply_content):
        """回复通知"""
        return cls.send(
            recipient_id=recipient_id,
            notification_type='reply',
            content=f"回复了你的评论",
            sender_id=sender_id,
            target_id=comment_id,
            target_type='comment',
            extra_data={
                'wallpaper_name': wallpaper_name,
                'reply_content': reply_content[:50]
            }
        )

    @classmethod
    def send_follow(cls, recipient_id, sender_id, follower_nickname):
        """关注通知"""
        return cls.send(
            recipient_id=recipient_id,
            notification_type='follow',
            content=f"关注了你",
            sender_id=sender_id,
            target_id=sender_id,
            target_type='user',
            extra_data={'follower_nickname': follower_nickname}
        )

    @classmethod
    def send_reward(cls, recipient_id, points, reason="系统奖励"):
        """积分奖励通知"""
        return cls.send(
            recipient_id=recipient_id,
            notification_type='reward',
            content=f"{reason} {points} 积分",
            sender_id=None, # 系统发送
            target_type='system',
            extra_data={'points': points}
        )

    @classmethod
    def send_announcement(cls, recipient_id, title, content):
        """系统公告通知"""
        return cls.send(
            recipient_id=recipient_id,
            notification_type='announcement',
            content=title,
            sender_id=None, # 系统发送
            target_type='system',
            extra_data={'detail_content': content}
        )
