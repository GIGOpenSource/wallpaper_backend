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
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

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
        ('system', '系统公告'),('feature', '更新公告'),('Activity', '活动公告'),
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
    CONFIG_TYPE_CHOICES = [('help', '帮助与支持'),('about', '关于'),('privacy', '隐私政策'),
        ('terms', '服务条款'),('basic_settings', '网站基础设置'),('robots_txt', 'Robots.txt'),
        ('sitemap', 'Sitemap'),('sitemap_url', 'Sitemap URL')]
    LANGUAGE_CHOICES = [('es', '西班牙语'),('en', '英语'),('pt', '葡萄牙语'),
        ('ja', '日语'),('ko', '韩语'),('zh-hans', '简体中文'),('zh-hant', '繁体中文'),
        ('de', '德语'),('fr', '法语'),
    ]
    config_type = models.CharField(max_length=20,choices=CONFIG_TYPE_CHOICES,verbose_name="配置类型")
    config_value = models.JSONField(default=dict,verbose_name="配置值")
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name="标题")
    content = models.TextField(blank=True, null=True, verbose_name="内容")  # 存储 URL 或富文本
    priority = models.IntegerField(default=0, verbose_name="优先级（数字越大越靠前）", db_index=True,blank=True)
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    language = models.CharField(max_length=10,choices=LANGUAGE_CHOICES,default='zh-hans',verbose_name="语言",
        blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 't_site_config'
        verbose_name = '网站配置'
        verbose_name_plural = '网站配置'
        ordering = ['config_type', '-updated_at']
        indexes = [
            models.Index(fields=['config_type']),
            models.Index(fields=['config_type', 'language']),
        ]

    def __str__(self):
        if self.language:
            return f"{self.get_config_type_display()} - {self.get_language_display()}"
        return f"{self.get_config_type_display()}"


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
    new_users_today = models.IntegerField(default=0, verbose_name="今日新增用户数")
    new_wallpapers_today = models.IntegerField(default=0, verbose_name="今日新增壁纸数")
    new_daily_active_users = models.IntegerField(default=0, verbose_name="今日新增日活跃用户数")
    new_weekly_active_users = models.IntegerField(default=0, verbose_name="今日新增周活跃用户数")
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
    handler = models.ForeignKey(User,on_delete=models.DO_NOTHING,null=True,blank=True,related_name="handled_reports",
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


class RecommendStrategy(models.Model):
    """
    推荐策略表：用于首页/热门推荐位策略配置
    """
    STRATEGY_TYPE_CHOICES = [
        ("home", "首页"),
        ("hot", "热门"),
        ("banner","轮播")
    ]
    STATUS_CHOICES = [
        ("draft", "草稿"),
        ("active", "生效中"),
        ("inactive", "停用"),
    ]
    PLATFORM_CHOICES = [
        ("all", "所有"),
        ("pc", "PC"),
        ("phone", "手机"),
    ]
    name = models.CharField(max_length=100, verbose_name="策略名称")
    priority = models.IntegerField(default=0, verbose_name="优先级（越大越优先）")
    content_limit = models.PositiveIntegerField(default=0, verbose_name="内容数量（0=不限制）")
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_TYPE_CHOICES, verbose_name="策略类型")
    apply_area = models.CharField(max_length=50, default="global", verbose_name="应用区域")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default="all", verbose_name="适用平台")
    start_time = models.DateTimeField(blank=True, null=True, verbose_name="生效开始时间")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="生效结束时间")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name="状态")
    stats_data = models.JSONField(default=dict, blank=True, verbose_name="统计数据")
    # wallpaper_ids = models.JSONField(default=list, blank=True, verbose_name="策略内容（壁纸ID列表）")
    remark = models.CharField(max_length=255, blank=True, null=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    # 生效模式固定区间 / 每日循环 / 每周循环
    TIME_MODE_CHOICES = (
        ("fixed", "固定区间"),  # 全时段：指定开始~结束时间
        ("daily", "每日循环"),  # 每天固定时间段生效
        ("weekly", "每周循环"),  # 每周几 + 时间段生效
    )
    time_mode = models.CharField(max_length=20, choices=TIME_MODE_CHOICES, default="fixed", verbose_name="生效模式",db_default="fixed",blank= True)
    class Meta:
        db_table = "t_recommend_strategy"
        verbose_name = "推荐策略"
        verbose_name_plural = "推荐策略"
        ordering = ["-priority", "-created_at"]
        indexes = [
            models.Index(fields=["strategy_type", "status"]),
            models.Index(fields=["apply_area", "status"]),
            models.Index(fields=["-priority"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.strategy_type}]"



class StrategyWallpaperRelation(models.Model):
    """
    策略壁纸关联表：用于管理推荐策略与壁纸的多对多关系
    删除此表不会影响策略表和壁纸表的数据完整性
    """
    strategy = models.ForeignKey(
        RecommendStrategy,
        on_delete=models.CASCADE,
        related_name="strategy_wallpaper_relations",
        verbose_name="推荐策略"
    )
    wallpaper = models.ForeignKey(
        Wallpapers,
        on_delete=models.CASCADE,
        related_name="strategy_wallpaper_relations",
        verbose_name="壁纸"
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序权重（数值越小越靠前）")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    class Meta:
        db_table = "t_strategy_wallpaper_relation"
        verbose_name = "策略壁纸关联"
        verbose_name_plural = "策略壁纸关联"
        unique_together = ('strategy', 'wallpaper')  # 确保同一策略不会重复关联同个壁纸
        ordering = ['strategy', 'sort_order', '-created_at']
        indexes = [
            models.Index(fields=['strategy', 'sort_order']),
            models.Index(fields=['wallpaper', '-created_at']),
        ]
    def __str__(self):
        return f"{self.strategy.name} → {self.wallpaper.name}"

class Role(models.Model):
    """
    角色表：独立于用户表的通用角色管理
    支持后台管理员(CustomerUser)和C端用户(User)两种用户类型
    """
    USER_TYPE_CHOICES = [
        ('admin', '后台管理员'),
        ('customer', 'C端用户'),
    ]
    name = models.CharField(max_length=50, unique=True, verbose_name="角色名称")
    code = models.CharField(max_length=50, unique=True, verbose_name="角色编码",
                            help_text="唯一标识，如：super_admin, admin, operator, user")
    description = models.TextField(blank=True, null=True, verbose_name="角色描述")
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, verbose_name="用户类型",
                                 help_text="区分后台管理员或C端用户")
    user_count = models.PositiveIntegerField(default=0, verbose_name="用户数量", help_text="拥有该角色的用户总数")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    sort_order = models.IntegerField(default=0, verbose_name="排序权重（数值越小越靠前）")
    permissions = models.JSONField(default=list, blank=True, verbose_name="权限列表", help_text="存储角色的权限配置")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    class Meta:
        db_table = 't_role'
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['user_type', 'sort_order', '-created_at']
        indexes = [
            models.Index(fields=['user_type', 'code']),
            models.Index(fields=['is_active']),
        ]
    def __str__(self):
        return f"{self.get_user_type_display()} - {self.name}"



class CustomerUserRole(models.Model):
    """
    C端用户角色关联表：用于管理CustomerUser与角色的多对多关系
    后台管理员(User)直接通过role字段关联Role.code，不需要此表
    """
    customer = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        related_name="role_relations",
        verbose_name="C端用户"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="customer_relations",
        verbose_name="角色",
        limit_choices_to={'user_type': 'customer'}
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="分配时间")
    class Meta:
        db_table = 't_customer_user_role'
        verbose_name = 'C端用户角色关联'
        verbose_name_plural = 'C端用户角色关联'
        unique_together = ('customer', 'role')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'role']),
        ]
    def __str__(self):
        return f"{self.customer.email} → {self.role.name}"


class OperationLog(models.Model):
    """
    操作日志表：记录管理端的操作行为
    """
    OPERATION_TYPES = [
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('query', '查询'),
        ('export', '导出'),
        ('import', '导入'),
        ('login', '登录'),
        ('logout', '登出'),
        ('audit', '审核'),
        ('other', '其他'),
    ]
    operator_id = models.IntegerField(null=True, blank=True, verbose_name="操作人ID",
                                      help_text="冗余字段，避免外键约束问题")
    operator_name = models.CharField(max_length=50, verbose_name="操作人姓名",
                                     help_text="冗余字段，避免操作人删除后无法查看")
    module = models.CharField(max_length=50, verbose_name="操作模块", help_text="如：用户管理、壁纸管理、角色管理")
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name="操作类型")
    target_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="操作对象ID")
    target_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="操作对象名称")
    description = models.TextField(blank=True, null=True, verbose_name="操作描述", help_text="详细操作说明")
    request_method = models.CharField(max_length=10, blank=True, null=True, verbose_name="请求方法",
                                      help_text="GET/POST/PUT/DELETE")
    request_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="请求URL")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP地址")
    user_agent = models.TextField(blank=True, null=True, verbose_name="用户代理")
    extra_data = models.JSONField(default=dict, blank=True, verbose_name="扩展数据", help_text="存储额外的操作详情")
    status = models.SmallIntegerField(default=1, choices=[(1, '成功'), (0, '失败')], verbose_name="操作状态")
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")
    class Meta:
        db_table = 't_operation_log'
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['operator_id', '-created_at']),
            models.Index(fields=['module', '-created_at']),
            models.Index(fields=['operation_type', '-created_at']),
        ]
    def __str__(self):
        return f"{self.operator_name} - {self.module} - {self.get_operation_type_display()} - {self.created_at}"


class PageTDK(models.Model):
    """
    页面TDK配置表：管理页面的Title、Description、Keywords（SEO优化）
    """
    PAGE_TYPE_CHOICES = [
        ('home', '首页'),
        ('category', '分类页'),
        ('tag', '标签页'),
        ('detail', '详情页'),
        ('search', '搜索页'),
        ('article', '文章页'),
        ('custom', '自定义页面'),
    ]
    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES, verbose_name="页面类型")
    title = models.CharField(max_length=200, verbose_name="页面标题（Title）")
    description = models.TextField(blank=True, null=True, verbose_name="页面描述（Description）")
    keywords = models.CharField(max_length=500, blank=True, null=True, verbose_name="关键词（Keywords）")
    url = models.ForeignKey(
        SiteConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="page_tdk_configs",
        verbose_name="关联URL",
        help_text="关联 sitemap_url 类型的配置记录",
        limit_choices_to={'config_type': 'sitemap_url'}
    )
    applied_count = models.PositiveIntegerField(default=0, verbose_name="应用页面数")
    is_template = models.BooleanField(default=False, verbose_name="是否为模板")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    class Meta:
        db_table = 't_page_tdk'
        verbose_name = '页面TDK配置'
        verbose_name_plural = '页面TDK配置'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['page_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['url', '-updated_at']),
        ]

    def __str__(self):
        url_str = self.url.content if self.url else '未关联'
        return f"{self.get_page_type_display()} - {url_str}"


class BacklinkManagement(models.Model):
    """
    外链管理表：管理网站的外链信息
    """
    STATUS_CHOICES = [
        ('active', '有效'),
        ('inactive', '失效'),
        ('pending', '待审核'),
        ('toxic', '有毒'),
    ]

    # Nofollow 对你SEO没用，不加权重 告诉搜索引擎：别信这个链接
    # UGC 用户生成内容（User Generated Content）
    # Dofollow 会给你的网站加分、提升排名
    # Sponsored 付费、广告、赞助链接 必须标这个，不传递权重
    ATTRIBUTE_CHOICES = [
        ('dofollow', 'Dofollow'),
        ('nofollow', 'Nofollow'),
        ('ugc', 'UGC'),
        ('sponsored', 'Sponsored'),
    ]
    
    BUILD_STATUS_CHOICES = [
        ('pending', '待建设'),
        ('completed', '已建设'),
    ]
    
    source_page = models.URLField(max_length=500, verbose_name="来源页面")
    target_page = models.URLField(max_length=500, verbose_name="目标页面")
    anchor_text = models.CharField(max_length=200, blank=True, null=True, verbose_name="锚文本")
    da_score = models.IntegerField(default=0, verbose_name="DA评分（Domain Authority）")
    quality_score = models.IntegerField(default=0, verbose_name="质量评分（0-100）")
    attribute = models.CharField(max_length=20, choices=ATTRIBUTE_CHOICES, default='dofollow', verbose_name="属性")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    build_status = models.CharField(max_length=20, choices=BUILD_STATUS_CHOICES, default='completed', verbose_name="建设状态")
    relevance = models.CharField(max_length=50, blank=True, null=True, verbose_name="相关性")
    contact_info = models.JSONField(blank=True, null=True, verbose_name="联系方式")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发现时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")

    class Meta:
        db_table = 't_backlink_management'
        verbose_name = '外链管理'
        verbose_name_plural = '外链管理'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['attribute']),
            models.Index(fields=['target_page']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.source_page} -> {self.target_page} ({self.anchor_text or '无锚文本'})"


class DomainAnalysis(models.Model):
    """
    域名分析表：存储域名的安全评分、外链数等信息
    """
    STATUS_CHOICES = [
        ('safe', '安全'),
        ('danger', '危险'),
    ]
    
    domain = models.CharField(max_length=255, unique=True, verbose_name="域名")
    safety_score = models.IntegerField(default=0, verbose_name="安全评分（0-100）")
    backlink_count = models.IntegerField(default=0, verbose_name="外链数")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='safe', verbose_name="状态")
    analyzed_at = models.DateTimeField(auto_now=True, verbose_name="分析时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")
    class Meta:
        db_table = 't_domain_analysis'
        verbose_name = '域名分析'
        verbose_name_plural = '域名分析'
        ordering = ['-analyzed_at']
        indexes = [
            models.Index(fields=['domain']),
            models.Index(fields=['status']),
            models.Index(fields=['-analyzed_at']),
        ]

    def __str__(self):
        return f"{self.domain} (评分: {self.safety_score}, 状态: {self.get_status_display()})"


class DetectionLog(models.Model):
    """
    检测日志表：记录外链和域名的检测日志
    """
    CATEGORY_CHOICES = [
        ('health_check', '健康度检查'),
        ('invalid_check', '失效检测'),
        ('new_discovery', '新外链发现'),
        ('domain_check', '域名检测'),
        ('full_scan', '全站扫描'),
        ('manual', '手动检测'),
    ]
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
        ('warning', '警告'),
    ]
    
    check_time = models.DateTimeField(auto_now_add=True, verbose_name="检测时间")
    content = models.TextField(verbose_name="检测内容")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="类别")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success', verbose_name="状态")
    result_summary = models.CharField(max_length=500, blank=True, null=True, verbose_name="结果摘要")
    operator = models.CharField(max_length=100, blank=True, null=True, verbose_name="操作人")
    
    class Meta:
        db_table = 't_detection_log'
        verbose_name = '检测日志'
        verbose_name_plural = '检测日志'
        ordering = ['-check_time']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['-check_time']),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.content[:50]}..."


class PageSpeed(models.Model):
    """
    页面速度表：存储页面性能指标数据
    """
    PLATFORM_CHOICES = [
        ('page', '桌面端'),
        ('phone', '手机'),
        ('pad', '平板'),
        ('optimization', '内容优化'),
    ]
    
    MOBILE_FRIENDLY_CHOICES = [
        ('friendly', '友好'),
        ('unfriendly', '不友好'),
    ]
    
    page_path = models.CharField(max_length=500, verbose_name="页面路径")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='page', verbose_name="平台/设备")
    full_url = models.URLField(max_length=1000, verbose_name="完整URL")
    overall_score = models.IntegerField(default=0, verbose_name="综合评分（0-100）")
    mobile_friendly = models.CharField(max_length=20, choices=MOBILE_FRIENDLY_CHOICES, blank=True, null=True, verbose_name="移动友好性")
    
    # 核心Web指标
    fcp = models.FloatField(default=0.0, verbose_name="FCP（首次内容绘制，秒）")
    lcp = models.FloatField(default=0.0, verbose_name="LCP（最大内容绘制，秒）")
    fid = models.FloatField(default=0.0, verbose_name="FID（首次输入延迟，毫秒）")
    inp = models.FloatField(default=0.0, verbose_name="INP（交互到下一次绘制，毫秒）")
    cls = models.FloatField(default=0.0, verbose_name="CLS（累积布局偏移）")
    ttfb = models.FloatField(default=0.0, verbose_name="TTFB（首字节时间，秒）")
    
    load_time = models.FloatField(default=0.0, verbose_name="加载时间（秒）")
    page_size = models.FloatField(default=0.0, verbose_name="页面大小（KB）")
    issue_count = models.IntegerField(default=0, verbose_name="问题数")
    
    # 资源分析相关字段
    resource_count = models.IntegerField(default=0, verbose_name="资源数量")
    loading_timeline = models.JSONField(blank=True, null=True, verbose_name="加载时间线")
    optimization_suggestions = models.JSONField(blank=True, null=True, verbose_name="优化建议（兼容旧数据）")
    
    tested_at = models.DateTimeField(auto_now=True, verbose_name="测试时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    
    # 内容优化相关字段
    page_title = models.CharField(max_length=500, blank=True, null=True, verbose_name="页面标题")
    content_score = models.IntegerField(default=0, verbose_name="内容评分（0-100）")
    word_count = models.IntegerField(default=0, verbose_name="字数")
    issues = models.JSONField(blank=True, null=True, verbose_name="问题检测")
    suggestions = models.JSONField(blank=True, null=True, verbose_name="优化建议")
    last_optimized_at = models.DateTimeField(blank=True, null=True, verbose_name="最后优化时间")

    class Meta:
        db_table = 't_page_speed'
        verbose_name = '页面速度'
        verbose_name_plural = '页面速度'
        ordering = ['-tested_at']
        indexes = [
            models.Index(fields=['page_path']),
            models.Index(fields=['platform']),
            models.Index(fields=['mobile_friendly']),
            models.Index(fields=['-overall_score']),
            models.Index(fields=['-tested_at']),
            # 联合唯一索引：同一页面路径+平台只能有一条记录
            models.Index(fields=['page_path', 'platform'], name='idx_page_platform'),
        ]
        unique_together = ('page_path', 'platform')

    def __str__(self):
        return f"{self.page_path} [{self.get_platform_display()}] (评分: {self.overall_score})"


class SEODashboardStats(models.Model):
    """
    SEO数据分析仪表统计表：存储每日SEO核心指标快照
    用于对比前一天/一周的数据变化趋势
    支持智能缓存：每10次请求调用一次GSC接口
    """
    site_url = models.CharField(max_length=500, verbose_name="网站URL")
    stat_date = models.DateField(verbose_name="统计日期")
    total_indexed = models.IntegerField(default=0, verbose_name="总收录量")
    seo_traffic = models.IntegerField(default=0, verbose_name="SEO流量")
    avg_ranking = models.FloatField(default=0.0, verbose_name="平均排名")
    backlink_count = models.IntegerField(default=0, verbose_name="外链数量")
    request_count = models.IntegerField(default=0, verbose_name="请求计数（用于控制GSC调用频率）")
    last_gsc_update = models.DateTimeField(blank=True, null=True, verbose_name="最后一次GSC更新时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 't_seo_dashboard_stats'
        verbose_name = 'SEO数据分析仪表'
        verbose_name_plural = 'SEO数据分析仪表'
        ordering = ['-stat_date']
        indexes = [
            models.Index(fields=['site_url', '-stat_date']),
            models.Index(fields=['-stat_date']),
        ]
        # 联合唯一索引：同一网站+日期只能有一条记录
        unique_together = ('site_url', 'stat_date')
    
    def __str__(self):
        return f"{self.site_url} - {self.stat_date} SEO统计数据"


class SEOInspection(models.Model):
    """
    SEO日常巡查表：存储各项SEO检查指标的结果
    支持分类：搜索与抓取、页面质量、安全巡查、性能巡查
    """
    CATEGORY_CHOICES = [
        ('search_crawl', '搜索与抓取'),
        ('page_quality', '页面质量'),
        ('security', '安全巡查'),
        ('performance', '性能巡查'),
    ]
    
    STATUS_CHOICES = [
        ('normal', '正常'),
        ('warning', '警告'),
        ('error', '异常'),
    ]
    
    # 固定的检查项（创建后不再修改）
    INSPECTION_ITEM_CHOICES = [
        # 搜索与抓取类
        ('indexed_pages', 'Indexed Pages'),
        ('discovered_pages', 'Discovered Pages'),
        ('googlebot_crawls_per_day', 'Googlebot Crawls/Day'),
        ('avg_response_time', 'Avg Response Time'),
        ('sitemap_status', 'Sitemap Status'),
        ('google_penalties', 'Google Penalties'),
        # 页面质量类
        ('http_status_code', 'HTTP状态码检测'),
        ('tdk_check', 'TDK完整性检查'),
        ('nofollow_external_links', 'Nofollow外链检测'),
        ('h_tag_structure', 'H标签结构检查'),
        # 安全巡查类（预留）
        # 性能巡查类（预留）
    ]
    
    site_url = models.CharField(max_length=500, verbose_name="网站URL")
    inspection_item = models.CharField(max_length=50, choices=INSPECTION_ITEM_CHOICES, verbose_name="检查项")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="应用分类")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='normal', verbose_name="状态")
    current_value = models.CharField(max_length=500, blank=True, null=True, verbose_name="当前值")
    threshold = models.CharField(max_length=500, blank=True, null=True, verbose_name="阈值")
    suggestion = models.TextField(blank=True, null=True, verbose_name="处理建议")
    problem_urls = models.JSONField(blank=True, null=True, verbose_name="问题URL列表")
    inspected_at = models.DateTimeField(auto_now_add=True, verbose_name="检查时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 't_seo_inspection'
        verbose_name = 'SEO日常巡查'
        verbose_name_plural = 'SEO日常巡查'
        ordering = ['-inspected_at']
        indexes = [
            models.Index(fields=['site_url', 'category']),
            models.Index(fields=['site_url', 'inspection_item']),
            models.Index(fields=['-inspected_at']),
        ]
        # 同一网站+检查项+分类的唯一约束
        unique_together = ('site_url', 'inspection_item', 'category')
    
    def __str__(self):
        return f"{self.site_url} - {self.get_inspection_item_display()} [{self.get_category_display()}]"


class Competitor(models.Model):
    """
    竞争对手表：存储竞争对手网站的SEO数据
    """
    name = models.CharField(max_length=200, verbose_name="网站名称")
    url = models.URLField(max_length=500, unique=True, verbose_name="网站URL")
    domain_authority = models.IntegerField(default=0, verbose_name="域名权重（DA）")
    monthly_traffic = models.BigIntegerField(default=0, verbose_name="月流量")
    keyword_count = models.IntegerField(default=0, verbose_name="关键词数")
    backlink_count = models.IntegerField(default=0, verbose_name="外链数")
    growth_trend = models.CharField(
        max_length=20,
        choices=[('up', '上升'), ('stable', '稳定'), ('down', '下降')],
        default='stable',
        verbose_name="增长趋势"
    )
    last_synced_at = models.DateTimeField(blank=True, null=True, verbose_name="最后同步时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 't_competitor'
        verbose_name = '竞争对手'
        verbose_name_plural = '竞争对手'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['url']),
            models.Index(fields=['-domain_authority']),
            models.Index(fields=['-monthly_traffic']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"
