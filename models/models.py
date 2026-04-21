#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：crushcheck
@File    ：models.py
@Author  ：LiangHB
@Date    ：2025/10/30 10:47 
@description : 数据模型（客户账户、壁纸等）
"""
from django.db import models
from django.utils import timezone
from tool.password_hasher import hash_password

class CustomerUser(models.Model):
    """
    C 端客户账户（邮箱 + 密码），与后台管理员 User 分离。
    """
    email = models.EmailField(unique=True, verbose_name="邮箱")
    password = models.CharField(max_length=256, verbose_name="密码（哈希）")
    nickname = models.CharField(max_length=50, blank=True, null=True, verbose_name="昵称")
    gender = models.SmallIntegerField(default=0, choices=[(0, "未知"), (1, "男"), (2, "女")], verbose_name="性别")
    avatar_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="头像URL")
    badge = models.JSONField(blank=True, null=True, default=list, verbose_name="用户勋章")
    last_login = models.DateTimeField(blank=True, null=True, verbose_name="最后登录时间")
    points = models.IntegerField(default=0, verbose_name="积分")
    level = models.IntegerField(default=1, verbose_name="等级")
    upload_count = models.IntegerField(default=0, verbose_name="上传数")
    collection_count = models.IntegerField(default=0, verbose_name="收藏数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    # 用户状态
    status = models.SmallIntegerField(default=1, choices=[(1, "正常"), (2, "禁用")], verbose_name="用户状态")

    class Meta:
        db_table = 't_customer_user'
        verbose_name = '客户用户'
        verbose_name_plural = '客户用户'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('$2b$'):
            self.password = hash_password(self.password[:72])
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

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


# 壁纸分类
class WallpaperCategory(models.Model):
    name = models.CharField(max_length=50, verbose_name="分类名称", unique=True)
    desc = models.CharField(max_length=200, verbose_name="分类描述", blank=True, null=True)
    sort = models.IntegerField(default=0, verbose_name="排序（数字越小越靠前）")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 't_wallpaper_category'
        verbose_name = '壁纸分类'
        verbose_name_plural = '壁纸分类'
        ordering = ['sort', '-created_at']  # 优先按排序，再按创建时间

    def __str__(self):
        return self.name


# 壁纸标签，可以有很多
class WallpaperTag(models.Model):
    name = models.CharField(max_length=50, verbose_name="标签名称", unique=True)
    wallpaper_count = models.PositiveIntegerField(default=0, verbose_name="壁纸总数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 't_wallpaper_tag'
        verbose_name = '壁纸标签'
        verbose_name_plural = '壁纸标签'

    def __str__(self):
        return self.name


# 壁纸
class Wallpapers(models.Model):
    name = models.CharField(max_length=200, verbose_name="壁纸名称")  # 加长长度适配英文标题
    url = models.URLField(max_length=500, verbose_name="壁纸原图链接")  # 加长URL长度
    thumb_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="壁纸缩略图链接")  # 新增：缩略图URL
    width = models.IntegerField(default=0, verbose_name="图片宽度")  # 新增：宽度
    height = models.IntegerField(default=0, verbose_name="图片高度")  # 新增：高度
    image_format = models.CharField(max_length=20, blank=True, null=True, verbose_name="图片格式")  # 新增：格式(jpg/png)
    source_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="图片来源链接")  # 新增：来源链接
    has_watermark = models.BooleanField(default=False, verbose_name="是否有水印",null= True,blank=True)  # 新增：水印标识
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    AUDIT_STATUS_CHOICES = [(None, '未审核'),('pending', '待审核'),('approved', '审核通过'),('rejected', '审核不通过')]
    audit_status = models.CharField(max_length=20,choices=AUDIT_STATUS_CHOICES,default=None,null=True,blank=True,
                                    verbose_name="审核状态",db_index=True  # 添加索引优化查询
    )
    audit_remark = models.TextField(blank=True, null=True, verbose_name="审核备注")
    audited_at = models.DateTimeField(blank=True, null=True, verbose_name="审核时间")
    category = models.ManyToManyField(WallpaperCategory, blank=True, verbose_name="所属分类")
    tags = models.ManyToManyField(WallpaperTag, blank=True, verbose_name="标签", related_name='wallpapers')
    is_live = models.BooleanField(default=False, verbose_name="是否Live壁纸",null= True,blank=True)
    is_hd = models.BooleanField(default=False, verbose_name="是否高清壁纸",null= True,blank=True)
    hot_score = models.IntegerField(default=0, verbose_name="热门分值（越高越热门）",blank=True)
    like_count = models.PositiveIntegerField(default=0, verbose_name="点赞数",blank=True)
    collect_count = models.PositiveIntegerField(default=0, verbose_name="收藏数",blank=True)
    download_count = models.PositiveIntegerField(default=0, verbose_name="下载量",blank=True)
    view_count = models.PositiveIntegerField(default=0, verbose_name="浏览量", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 't_wallpapers'
        verbose_name = '壁纸'
        verbose_name_plural = '壁纸'
        ordering = ['-created_at']

    def __str__(self):
        return self.name[:50]  # 截断过长名称

    def get_category_names(self):
        """返回拼接的分类名称，如「静态 + 手机」"""
        categories = self.category.all()
        if not categories:
            return "未分类"
        return " + ".join([cat.name for cat in categories])

    def is_hd_auto(self):
        """根据分辨率自动判断是否高清（可选）"""
        # 简单判断：宽度≥1920 或 高度≥1080 视为高清
        return self.width >= 1920 or self.height >= 1080


class CustomerWallpaperUpload(models.Model):
    """
    用户上传记录：与爬取的 Wallpapers 主数据分离，仅当有 C 端上传时存在一行。
    """
    wallpaper = models.OneToOneField(
        Wallpapers,
        on_delete=models.CASCADE,
        related_name="customer_upload",
        verbose_name="壁纸",
    )
    customer = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        related_name="wallpaper_uploads",
        verbose_name="上传用户",
    )
    cos_key = models.CharField(max_length=500, blank=True, null=True, verbose_name="COS 对象键")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        db_table = "t_customer_wallpaper_upload"
        verbose_name = "用户壁纸上传"
        verbose_name_plural = "用户壁纸上传"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.email} → #{self.wallpaper_id}"


class WallpaperLike(models.Model):
    customer = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        related_name="wallpaper_likes",
        verbose_name="用户",
    )
    wallpaper = models.ForeignKey(
        Wallpapers,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name="壁纸",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="点赞时间")

    class Meta:
        db_table = 't_wallpaper_like'
        verbose_name = '壁纸点赞'
        verbose_name_plural = '壁纸点赞'
        unique_together = ('customer', 'wallpaper')

    def __str__(self):
        return f"{self.customer.email} → {self.wallpaper.name[:30]}"


class WallpaperCollection(models.Model):
    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        related_name="wallpaper_collections",
        verbose_name="收藏用户",
    )
    wallpaper = models.ForeignKey(
        Wallpapers,
        on_delete=models.CASCADE,
        related_name="collections",
        verbose_name="收藏壁纸",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        db_table = 't_wallpaper_collection'
        verbose_name = '壁纸收藏'
        verbose_name_plural = '壁纸收藏'
        unique_together = ('user', 'wallpaper')

    def __str__(self):
        return f"{self.user.email} - {self.wallpaper.name}"


class NavigationTag(models.Model):
    """
    前端导航分类标签（后台可控）
    - 关联壁纸标签（Tag）
    - 支持地区标识
    - 支持排序、显示/隐藏控制
    """
    # 关联的壁纸标签（一对一/多对一，根据实际需求选择）
    # 推荐一对一：一个导航标签对应一个壁纸标签，便于管理
    tag = models.OneToOneField(WallpaperTag,on_delete=models.CASCADE,verbose_name="关联壁纸标签",related_name="navigation_tag")
    # 地区标识（用于区分不同地区的导航标签）
    region = models.CharField(max_length=20,default='global',verbose_name="所属地区")
    # 导航展示相关字段
    nav_name = models.CharField(max_length=50,verbose_name="导航显示名称",help_text="可自定义导航栏显示的名称，不填则使用标签名称")
    wallpaper_count = models.PositiveIntegerField(default=0, verbose_name="壁纸总数")  # 新增
    sort = models.IntegerField(default=0,verbose_name="导航排序（数字越小越靠前）")
    is_show = models.BooleanField(default=True,verbose_name="是否在前端显示")
    created_at = models.DateTimeField(auto_now_add=True,verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True,verbose_name="更新时间")

    class Meta:
        db_table = 't_navigation_tag'
        verbose_name = '导航分类标签'
        verbose_name_plural = '导航分类标签'
        ordering = ['sort', '-created_at']

    def __str__(self):
        return f"{self.get_region_display()} - {self.nav_name or self.tag.name}"

    def save(self, *args, **kwargs):
        # 自动填充导航名称（如果未填写则使用标签名称）
        if not self.nav_name:
            self.nav_name = self.tag.name
        super().save(*args, **kwargs)


class CarouselBanner(models.Model):
    """
    轮播图表
    存储下载量最高的前6名壁纸ID
    """
    wallpaper = models.ForeignKey(Wallpapers, on_delete=models.CASCADE, verbose_name="壁纸", related_name="carousel_banners")
    sort = models.IntegerField(default=0, verbose_name="轮播排序（数字越小越靠前）")
    download_count = models.IntegerField(default=0, verbose_name="下载量")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    class Meta:
        db_table = 't_carousel_banner'
        verbose_name = '轮播图'
        verbose_name_plural = '轮播图'
        ordering = ['sort', '-download_count']

    def __str__(self):
        return f"轮播图 {self.sort} - {self.wallpaper.name[:30]}"


class WallpaperComment(models.Model):
    """
    壁纸评论表
    """
    customer = models.ForeignKey(CustomerUser,on_delete=models.CASCADE,related_name="comments",verbose_name="评论用户"
    )
    wallpaper = models.ForeignKey(Wallpapers,on_delete=models.CASCADE,related_name="comments",verbose_name="壁纸"
    )
    parent = models.ForeignKey('self',on_delete=models.CASCADE,null=True,blank=True,related_name="replies",verbose_name="父评论（用于回复）"
    )
    content = models.TextField(verbose_name="评论内容")
    like_count = models.PositiveIntegerField(default=0, verbose_name="点赞数")
    is_hidden = models.BooleanField(default=False, verbose_name="是否隐藏")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 't_wallpaper_comment'
        verbose_name = '壁纸评论'
        verbose_name_plural = '壁纸评论'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallpaper', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
        ]

    def __str__(self):
        return f"{self.customer.email} → {self.wallpaper.name[:30]}"


class WallpaperCommentLike(models.Model):
    """
    壁纸评论点赞表
    """
    customer = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        related_name="comment_likes",
        verbose_name="用户",
    )
    comment = models.ForeignKey(
        WallpaperComment,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name="评论",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="点赞时间")

    class Meta:
        db_table = 't_wallpaper_comment_like'
        verbose_name = '评论点赞'
        verbose_name_plural = '评论点赞'
        unique_together = ('customer', 'comment')
        indexes = [
            models.Index(fields=['comment', '-created_at']),
        ]

    def __str__(self):
        return f"{self.customer.email} → Comment #{self.comment_id}"

class Notification(models.Model):
    """
    通知表（点赞提示、评论提示、粉丝提示、系统公告统一存储）
    使用 JSONField 存储不同类型通知的扩展数据，减少表数量
    """
    NOTIFICATION_TYPES = [
        ('like', '点赞'),('comment', '评论'),('follow', '关注'),('reply', '回复'),
        ('announcement', '系统公告'),
    ]

    recipient = models.ForeignKey(CustomerUser,on_delete=models.CASCADE,related_name="notifications",verbose_name="接收者"
    )
    sender = models.ForeignKey(CustomerUser,on_delete=models.SET_NULL,null=True,blank=True,related_name="sent_notifications",verbose_name="发送者"
    )
    notification_type = models.CharField(max_length=20,choices=NOTIFICATION_TYPES,verbose_name="通知类型"
    )
    target_id = models.PositiveIntegerField(verbose_name="目标对象ID（壁纸ID或评论ID）", null=True, blank=True)
    target_type = models.CharField(max_length=50, verbose_name="目标类型（wallpaper/comment/user）", null=True, blank=True)
    extra_data = models.JSONField(blank=True, null=True, default=dict, verbose_name="扩展数据")
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 't_notification'
        verbose_name = '用户通知'
        verbose_name_plural = '用户通知'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'notification_type']),
        ]

    def __str__(self):
        if self.notification_type == 'announcement':
            return f"系统公告 → {self.recipient.email}"
        return f"{self.sender.email} → {self.recipient.email} [{self.notification_type}]"



class UserFollow(models.Model):
    """
    用户关注表（粉丝关系）
    """
    follower = models.ForeignKey(CustomerUser,on_delete=models.CASCADE,related_name="following",verbose_name="关注者"
    )
    following = models.ForeignKey(CustomerUser,on_delete=models.CASCADE,related_name="followers",verbose_name="被关注者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="关注时间")

    class Meta:
        db_table = 't_user_follow'
        verbose_name = '用户关注'
        verbose_name_plural = '用户关注'
        unique_together = ('follower', 'following')
        indexes = [
            models.Index(fields=['following', '-created_at']),
            models.Index(fields=['follower', '-created_at']),
        ]

    def __str__(self):
        return f"{self.follower.email} → {self.following.email}"


class UserNotificationSettings(models.Model):
    user = models.OneToOneField(CustomerUser, on_delete=models.CASCADE, related_name='notification_settings')
    enable_like_notification = models.BooleanField(default=True)
    enable_comment_notification = models.BooleanField(default=True)
    enable_reply_notification = models.BooleanField(default=True)
    enable_follow_notification = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class SiteConfig(models.Model):
    """
    网站配置表：存储帮助与支持、关于、隐私政策等富文本内容
    """
    CONFIG_TYPE_CHOICES = [
        ('help', '帮助与支持'),
        ('about', '关于'),
        ('privacy', '隐私政策'),
        ('terms', '服务条款'),
    ]
    
    config_type = models.CharField(
        max_length=20,
        choices=CONFIG_TYPE_CHOICES,
        unique=True,
        verbose_name="配置类型"
    )
    title = models.CharField(max_length=200, verbose_name="标题")
    content = models.TextField(verbose_name="富文本内容")  # 存储 HTML 富文本
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 't_site_config'
        verbose_name = '网站配置'
        verbose_name_plural = '网站配置'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.get_config_type_display()} - {self.title}"


class DashboardStats(models.Model):
    """
    面板统计表：存储每日统计数据快照
    每天8:00后第一次请求时更新当日数据，避免频繁查询数据库
    """
    stat_date = models.DateField(unique=True, verbose_name="统计日期")
    total_users = models.IntegerField(default=0, verbose_name="总用户数量")
    total_wallpapers = models.IntegerField(default=0, verbose_name="总壁纸数量")
    total_views = models.BigIntegerField(default=0, verbose_name="总浏览量")
    total_downloads = models.BigIntegerField(default=0, verbose_name="总下载量")
    total_likes = models.IntegerField(default=0, verbose_name="总点赞数")
    total_collections = models.IntegerField(default=0, verbose_name="总收藏数")
    daily_active_users = models.IntegerField(default=0, verbose_name="日活跃用户数")
    weekly_active_users = models.IntegerField(default=0, verbose_name="周活跃用户数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 't_dashboard_stats'
        verbose_name = '面板统计数据'
        verbose_name_plural = '面板统计数据'
        ordering = ['-stat_date']
        indexes = [
            models.Index(fields=['-stat_date']),
        ]
    
    def __str__(self):
        return f"{self.stat_date} 统计数据"


class DashboardStats(models.Model):
    """
    面板统计表：存储每日统计数据快照
    每天8:00后第一次请求时更新当日数据，避免频繁查询数据库
    """
    stat_date = models.DateField(unique=True, verbose_name="统计日期")
    total_users = models.IntegerField(default=0, verbose_name="总用户数量")
    total_wallpapers = models.IntegerField(default=0, verbose_name="总壁纸数量")
    total_views = models.BigIntegerField(default=0, verbose_name="总浏览量")
    total_downloads = models.BigIntegerField(default=0, verbose_name="总下载量")
    total_likes = models.IntegerField(default=0, verbose_name="总点赞数")
    total_collections = models.IntegerField(default=0, verbose_name="总收藏数")
    daily_active_users = models.IntegerField(default=0, verbose_name="日活跃用户数")
    weekly_active_users = models.IntegerField(default=0, verbose_name="周活跃用户数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 't_dashboard_stats'
        verbose_name = '面板统计数据'
        verbose_name_plural = '面板统计数据'
        ordering = ['-stat_date']
        indexes = [
            models.Index(fields=['-stat_date']),
        ]

    def __str__(self):
        return f"{self.stat_date} 统计数据"


class Report(models.Model):
    """
    举报表：记录用户对壁纸或评论的举报
    """
    REPORT_TYPE_CHOICES = [('wallpaper', '壁纸'),('comment', '评论'),('user', '用户'),]
    REPORT_REASON_CHOICES = [('inappropriate', '内容不当'),('copyright', '侵权'),('spam', '垃圾信息'),('harassment', '骚扰'),
        ('violence', '暴力'),('pornography', '色情'),('political', '政治敏感'),('other', '其他'),
    ]
    REPORT_STATUS_CHOICES = [('pending', '待处理'),('processing', '处理中'),('resolved', '已解决'),('rejected', '已驳回'),]
    reporter = models.ForeignKey(CustomerUser,on_delete=models.CASCADE,related_name="reports",verbose_name="举报人")
    target_id = models.PositiveIntegerField(verbose_name="举报对象ID")
    target_type = models.CharField(max_length=20,choices=REPORT_TYPE_CHOICES,verbose_name="举报对象类型")
    reason = models.CharField(max_length=20,choices=REPORT_REASON_CHOICES,verbose_name="举报原因")
    detail = models.TextField(blank=True, null=True, verbose_name="详细说明")
    status = models.CharField(max_length=20,choices=REPORT_STATUS_CHOICES,default='pending',verbose_name="处理状态")
    handler = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="handled_reports",
                                verbose_name="处理人",db_constraint=False  # 不创建数据库外键约束
    )
    handle_result = models.TextField(blank=True, null=True, verbose_name="处理结果")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="举报时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    handled_at = models.DateTimeField(blank=True, null=True, verbose_name="处理时间")

    class Meta:
        db_table = 't_report'
        verbose_name = '举报记录'
        verbose_name_plural = '举报记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['reporter', '-created_at']),
            models.Index(fields=['target_type', 'target_id']),
        ]

    def __str__(self):
        return f"{self.reporter.email} 举报 {self.get_report_type_display()} #{self.target_id}"
