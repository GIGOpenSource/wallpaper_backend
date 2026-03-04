#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：crushcheck
@File    ：models.py
@Author  ：LiangHB
@Date    ：2025/10/30 10:47 
@description : 微信小程序用户模型
"""

from django.db import models
from django.utils import timezone
from tool.password_hasher import hash_password

class WeChatUser(models.Model):
    """
    微信小程序用户模型
    """
    # 用户唯一标识
    open_id = models.CharField(max_length=64, unique=True, verbose_name="用户OpenID")
    # 用户昵称
    username = models.CharField(max_length=100, blank=True, null=True, verbose_name="用户名")
    # 用户头像URL
    user_avatar = models.TextField(blank=True, null=True, verbose_name="用户头像")
    GENDER_TYPE = {'male': '男', 'female': '女', 'unknown': '未知'}
    user_gender = models.CharField(blank=True, null=True, choices=GENDER_TYPE, verbose_name="性别")
    user_telphone = models.CharField(max_length=30, blank=True, null=True, verbose_name="手机号")
    # 是否为VIP用户
    is_vip = models.BooleanField(default=False, verbose_name="是否为VIP")
    # VIP类型选择
    MONTHLY = 'monthly'
    ONCE = 'once'
    VIP_TYPE_CHOICES = [(MONTHLY, '月付'), (ONCE, '单次')]
    vip_type = models.CharField(max_length=20, choices=VIP_TYPE_CHOICES, blank=True, null=True, verbose_name="VIP类型")
    session_key = models.CharField(max_length=120, blank=True, null=True, verbose_name="Session Key")
    # 分享次数统计
    share_success_count = models.PositiveIntegerField(default=0, verbose_name="分享成功次数")
    # 成功次数统计
    allow_count = models.PositiveIntegerField(default=0, verbose_name="允许使用次数")
    # 失败次数统计
    fail_count = models.PositiveIntegerField(default=0, verbose_name="失败次数")
    # VIP到期日期
    vip_expire_date = models.DateTimeField(blank=True, null=True, verbose_name="VIP到期日")
    # 创建时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    STATUS_CHOICES = (
        (0, '正常'),
        (1, '冻结'),
        (2, '注销'),
        (3, '注销中'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name="用户状态")
    platform = models.CharField(max_length=20, blank=True, null=True, verbose_name="平台")

    is_deleted = models.BooleanField(default=False, verbose_name="是否已注销")
    delete_requested_at = models.DateTimeField(null=True, blank=True, verbose_name="注销请求时间")
    deletion_deadline = models.DateTimeField(null=True, blank=True, verbose_name="注销截止时间（7天后）")

    # xhs_mini fbook_mini ins_mini google_mini ios_mini apk_mini wechat_mini mock_mini
    class Meta:
        db_table = 'wx_wechat_user'
        verbose_name = '微信用户'
        verbose_name_plural = '微信用户'
        managed = False

    def __str__(self):
        return f"{self.username} ({self.open_id})"

    def get_invitees_count(self):
        """
        获取该用户邀请的人数
        """
        return self.invitations_sent.count()

    def request_account_deletion(self):
        """
        请求账户注销，设置7天冷静期
        """
        from datetime import datetime, timedelta
        self.is_deleted = True
        self.delete_requested_at = datetime.now()
        self.deletion_deadline = datetime.now() + timedelta(days=7)
        self.status = 2  # 设置为注销状态
        self.save()

    def cancel_account_deletion(self):
        """
        取消账户注销请求
        """
        self.is_deleted = False
        self.delete_requested_at = None
        self.deletion_deadline = None
        self.status = 0  # 恢复为正常状态
        self.save()

    def is_in_deletion_period(self):
        """检查是否仍在删除期限内"""
        if not self.is_deleted or not self.deletion_deadline:
            return False

        # 使用带时区的当前时间进行比较
        from django.utils import timezone
        current_time = timezone.now()

        # 比较当前时间是否仍在删除截止日期之前
        return current_time < self.deletion_deadline

    def can_be_permanently_deleted(self):
        """
        检查用户是否可以被永久删除（冷静期已过）
        """
        if self.is_deleted and self.deletion_deadline:
            from datetime import datetime
            return datetime.now() >= self.deletion_deadline
        return False


class User(models.Model):
    username = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=256)  # 存储自定义加密后的密码
    ROLE_CHOICES = [
        ('super_admin', '超级管理员'),
        ('admin', '管理员'),
        ('operator', '操作员'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='operator',
        verbose_name="用户角色"
    )
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="手机号")
    last_login = models.DateTimeField(blank=True, null=True, verbose_name="最后登录时间")
    # 创建时间
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    # 更新时间
    updated_at = models.DateTimeField(default=timezone.now, verbose_name="更新时间")

    def save(self, *args, **kwargs):
        # 仅在密码未加密时进行加密（避免更新用户时重复加密）
        if not self.password.startswith('$2b$'):  # bcrypt 哈希以 $2b$ 开头
            self.password = hash_password(self.password[:72])
        super().save(*args, **kwargs)

        # 最后登录时间

    class Meta:
        db_table = 'c_user'
        verbose_name = '后台管理员'
        verbose_name_plural = '后台管理员'
        ordering = ['-created_at']
        managed = False
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class InvitationRecord(models.Model):
    """
    邀请记录模型：记录用户之间的邀请关系
    """
    inviter = models.ForeignKey(
        WeChatUser,
        on_delete=models.CASCADE,
        related_name="invitations_sent",
        verbose_name="邀请人"
    )
    invitee = models.OneToOneField(
        WeChatUser,
        on_delete=models.CASCADE,
        related_name="invitation_received",
        verbose_name="被邀请人"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="邀请时间")

    class Meta:
        db_table = 'wx_invitation_record'
        verbose_name = '邀请记录'
        verbose_name_plural = '邀请记录'
        unique_together = ('invitee',)  # 确保每个用户只能被邀请一次

    def __str__(self):
        return f"{self.inviter.username} 邀请了 {self.invitee.username}"

class Wallpapers(models.Model):
    name = models.CharField(max_length=100, verbose_name="壁纸名称")
    url = models.URLField(verbose_name="壁纸链接")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 't_wallpapers'
        verbose_name = '壁纸'
        verbose_name_plural = '壁纸'