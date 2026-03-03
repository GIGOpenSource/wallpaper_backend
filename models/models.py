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

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class AIConfig(models.Model):
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('azure_openai', 'Azure OpenAI'),
        ('anthropic', 'Anthropic'),
        ('google', 'Google Gemini'),
        ('deepseek', 'DeepSeek'),
        ('custom', 'Custom'),
    ]
    user = models.ForeignKey(
        WeChatUser,
        on_delete=models.CASCADE,  # 若用户删除，其海报也删除
        related_name="aiconfigs",  # 反向关联：user.posters可获取用户所有海报
        verbose_name="关联用户",
        blank=True, null=True
    )
    email = models.EmailField(blank=True, null=True, verbose_name="邮箱")
    name = models.CharField(max_length=100, help_text='配置名称', blank=True)
    provider = models.CharField(max_length=32, help_text='厂商', blank=True)
    model = models.CharField(max_length=100, help_text='模型名称/版本', blank=True)
    enabled = models.BooleanField(default=True, help_text='是否启用', blank=True)
    is_default = models.BooleanField(default=False, help_text='是否设为默认（全局唯一）', blank=True)
    priority = models.IntegerField(default=0, help_text='优先级，数值越大优先', blank=True)
    # 凭据与连接
    api_key = models.CharField(max_length=256, help_text='访问密钥，读取时应掩码', blank=True)
    base_url = models.URLField(blank=True, help_text='自定义 API Base URL（代理/Azure 场景）')
    region = models.CharField(max_length=50, blank=True, help_text='区域（Azure 等需要）')
    api_version = models.CharField(max_length=50, blank=True, help_text='API 版本（Azure/OpenAI 兼容接口）')
    organization_id = models.CharField(max_length=100, blank=True, help_text='组织/项目标识（可选）')
    # 审计
    created_at = models.DateTimeField(blank=True, null=True, help_text='创建时间')
    updated_at = models.DateTimeField(blank=True, null=True, help_text='更新时间')

    class Meta:
        ordering = ['-is_default', '-priority', 'name']
        db_table = 'wx_aiconfig'

    def __str__(self) -> str:
        return f"{self.name} ({self.provider}:{self.model})"


class Product(models.Model):
    """
    商品模型
    """
    # 商品名称（必填，限制长度避免过长）
    name = models.CharField(max_length=200, verbose_name="商品名称")
    # vip \ once
    product_type = models.CharField(max_length=20, verbose_name="商品类型")
    # 商品价格（精确到分，避免浮点误差，max_digits根据业务定价范围调整）
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="商品售价")
    # 商品状态（比“上下架”更细化，覆盖全生命周期）
    STATUS_CHOICES = (
        ("on_sale", "上架销售"), ("off_sale", "下架"), ("out_of_stock", "缺货"), ("pre_sale", "预售"),
        ("discontinued", "已停产"),)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="off_sale", verbose_name="商品状态")
    # 创建时间（自动记录商品创建时间）
    created_time = models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name="创建时间")
    # 更新时间（自动记录最后修改时间，如改价格、库存等）
    updated_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    # 商品logo URL（主图，支持云存储URL或本地路径）
    logo_url = models.CharField(verbose_name="商品主图URL")
    # 商品描述（支持长文本，可包含规格、详情等）
    description = models.TextField(blank=True, null=True, verbose_name="商品描述")
    # 商品编号（唯一标识，便于内部管理和前端展示，如SKU）
    product_code = models.CharField(max_length=50, verbose_name="商品编号")
    # 是否为推荐商品（用于首页、热门商品栏展示）
    is_recommended = models.BooleanField(default=False, verbose_name="是否推荐")
    days = models.IntegerField(default=0, verbose_name="充值天数")
    region = models.CharField(max_length=50, blank=True, null=True, verbose_name="地区区域")

    class Meta:
        db_table = "wx_product"
        verbose_name = "商品"
        verbose_name_plural = "商品"
        # 常用查询索引（如按类型、状态、创建时间筛选）
        indexes = [
            models.Index(fields=["product_type", "status"]),
            models.Index(fields=["created_time"]),  # 按创建时间排序（新品）
            models.Index(fields=["is_recommended"]),  # 推荐商品快速查询
        ]
        # 默认按创建时间倒序（新商品在前）
        ordering = ["-created_time"]

    def save(self, *args, **kwargs):
        """
        重写save方法，在创建时自动生成商品编号
        """
        if not self.pk and not self.product_code:
            self.product_code = self.generate_product_code()
        super().save(*args, **kwargs)

    def generate_product_code(self):
        """
        根据商品类型生成商品编号
        格式: 类型前缀 + 年月日 + 4位序号
        例如: ELECT202510300001
        """
        from datetime import datetime

        # 类型映射字典
        type_mapping = {'vip': 'VIP'}

        # 获取类型前缀，如果没有映射则使用类型的前4个字符
        prefix = type_mapping.get(self.product_type, self.product_type[:4].upper())

        # 获取当前日期
        date_str = datetime.now().strftime('%Y%m%d')

        # 生成序号（基于当天该类型商品数量）
        today_products = Product.objects.filter(
            product_type=self.product_type,
            created_time__date=datetime.now().date()
        ).count()

        # 序号从0001开始
        sequence = str(today_products + 1).zfill(4)

        return f"{prefix}{date_str}{sequence}"


class WeChatPayOrder(models.Model):
    """
    微信支付订单模型
    """
    # 交易状态（对应微信支付官方状态，必须准确匹配）
    TRADE_STATE_CHOICES = (
        ("SUCCESS", "支付成功"), ("REFUND", "转入退款"), ("NOTPAY", "未支付"), ("CLOSED", "已关闭"),
        ("REVOKED", "已撤销（仅付款码支付）"),
        ("USERPAYING", "用户支付中（仅付款码支付）"), ("PAYERROR", "支付失败（仅付款码支付）"),)
    # 交易类型（微信支付支持的支付方式）
    TRADE_TYPE_CHOICES = (
        ("JSAPI", "小程序支付/公众号支付"), ("NATIVE", "扫码支付"), ("APP", "APP支付"), ("MWEB", "H5支付"),
        ("MICROPAY", "付款码支付"),
    )
    # 货币类型（默认人民币）
    FEE_TYPE_CHOICES = (("CNY", "人民币"),)
    # 1. 订单核心标识
    out_trade_no = models.CharField(max_length=32, unique=True, verbose_name="商户订单号（系统内部唯一）")
    transaction_id = models.CharField(max_length=32, blank=True, null=True,
                                      verbose_name="微信支付订单号（微信返回，唯一）")
    # 2. 金额信息（微信支付以“分”为单位，用整数存储避免精度问题）
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="订单总金额", blank=True)  # 应收总额
    payer_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="用户实际支付金额",
                                      blank=True)  # 可能含折扣
    fee_type = models.CharField(max_length=16, choices=FEE_TYPE_CHOICES, default="CNY", verbose_name="货币类型",
                                blank=True)
    # 3. 支付人信息（关联用户表+冗余关键信息）
    payer = models.ForeignKey(WeChatUser, on_delete=models.SET_NULL, related_name="pay_orders", verbose_name="支付人",
                              blank=True, null=True)
    openid = models.CharField(max_length=64, verbose_name="支付人OpenID", blank=True)  # 和用户表一致，便于快速查询
    payer_account = models.CharField(max_length=64, blank=True, null=True,
                                     verbose_name="付款账号（如银行卡尾号，微信返回）")
    # 4. 商品信息（关联商品表+冗余名称）
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, related_name="orders", verbose_name="关联商品",
                                blank=True, null=True)
    product_name = models.CharField(max_length=200, verbose_name="商品名称（冗余）", blank=True)  # 下单时的商品名称，避免商品改名影响订单
    # 5. 微信支付配置信息
    mch_id = models.CharField(max_length=32, verbose_name="商户号", blank=True)  # 微信支付分配的商户id
    appid = models.CharField(max_length=32, verbose_name="小程序AppID", blank=True)  # 微信分配的小程序id
    sub_mch_id = models.CharField(max_length=32, blank=True, null=True, verbose_name="子商户号（服务商模式时使用）")
    # 6. 交易状态信息
    trade_type = models.CharField(max_length=16, choices=TRADE_TYPE_CHOICES, verbose_name="交易类型", blank=True)
    trade_state = models.CharField(max_length=32, choices=TRADE_STATE_CHOICES, default="NOTPAY",
                                   verbose_name="交易状态", blank=True)
    bank_type = models.CharField(max_length=32, blank=True, null=True,
                                 verbose_name="付款银行（如ICBC_DEBIT=工商银行借记卡）")
    # 7. 时间信息（全生命周期时间戳）
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="订单创建时间", blank=True)  # 系统下单时间
    pay_time = models.DateTimeField(blank=True, null=True, verbose_name="支付完成时间（微信返回）")
    close_time = models.DateTimeField(blank=True, null=True, verbose_name="订单关闭时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="订单信息最后更新时间")  # 状态变更时更新
    notify_time = models.DateTimeField(blank=True, null=True, verbose_name="微信支付回调通知时间")  # 接收微信回调的时间
    # 8. 回调处理标识（避免重复处理回调）
    is_notify_processed = models.BooleanField(default=False, verbose_name="是否已处理回调通知", blank=True)
    # 9. 附加信息（可选）
    body = models.CharField(max_length=128, blank=True, null=True, verbose_name="订单描述（传给微信的备注）")
    attach = models.CharField(max_length=128, blank=True, null=True, verbose_name="附加数据（商户自定义，如订单来源）")
    posterId = models.CharField(max_length=64, blank=True, null=True, verbose_name="海报ID")

    class Meta:
        db_table = "wx_order"
        verbose_name = "微信支付订单"
        verbose_name_plural = "微信支付订单"
        # 核心索引：按订单号、微信交易号、用户、状态快速查询
        indexes = [
            models.Index(fields=["out_trade_no"]),
            models.Index(fields=["transaction_id"]),  # 微信交易号唯一，用于对账
            models.Index(fields=["payer", "trade_state"]),  # 查询用户的订单状态
            models.Index(fields=["created_time"]),  # 按时间筛选订单
            models.Index(fields=["trade_state", "created_time"]),  # 筛选特定状态的订单（如未支付）
        ]
        ordering = ["-created_time"]  # 默认按创建时间倒序（新订单在前）

