#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
初始化网站配置数据
使用方法：python init_site_config.py
"""
import os
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WallPaper.settings.pro')
django.setup()

from models.models import SiteConfig


def init_site_config():
    """初始化网站配置数据"""
    
    configs = [
        {
            'config_type': 'help',
            'title': '帮助与支持',
            'content': '''
<h2>帮助中心</h2>
<p>欢迎使用我们的壁纸平台！如果您在使用过程中遇到任何问题，请查看以下常见问题。</p>

<h3>常见问题</h3>
<ul>
    <li><strong>如何下载壁纸？</strong><br>点击壁纸详情页的"下载"按钮即可下载高清原图。</li>
    <li><strong>如何上传壁纸？</strong><br>登录后，在个人中心点击"上传壁纸"，选择图片并填写相关信息。</li>
    <li><strong>如何收藏壁纸？</strong><br>在壁纸详情页点击"收藏"按钮，即可将壁纸添加到您的收藏夹。</li>
    <li><strong>忘记密码怎么办？</strong><br>在登录页面点击"忘记密码"，通过邮箱重置密码。</li>
</ul>

<h3>联系我们</h3>
<p>如果您有其他问题，请通过以下方式联系我们：</p>
<ul>
    <li>邮箱：support@example.com</li>
    <li>工作时间：周一至周五 9:00-18:00</li>
</ul>
            ''',
            'is_active': True,
        },
        {
            'config_type': 'about',
            'title': '关于我们',
            'content': '''
<h2>关于我们</h2>
<p>我们是一个专注于提供高质量壁纸的平台，致力于为用户带来最佳的视觉体验。</p>

<h3>我们的使命</h3>
<p>为用户提供丰富、高清、多样化的壁纸资源，让每一台设备都能展现独特的个性与美感。</p>

<h3>我们的特色</h3>
<ul>
    <li>📱 支持多平台：PC 和手机壁纸全覆盖</li>
    <li>🎨 分类精细：按风格、颜色、分辨率等多维度分类</li>
    <li>⚡ 高速下载：优化的 CDN 加速，下载速度快</li>
    <li>👥 社区互动：用户可以上传、分享、评论壁纸</li>
    <li>🌟 个性化推荐：基于您的喜好智能推荐壁纸</li>
</ul>

<h3>发展历程</h3>
<p>自创立以来，我们已经服务了数百万用户，积累了海量的优质壁纸资源。未来，我们将继续优化用户体验，提供更多创新功能。</p>

<h3>加入我们</h3>
<p>如果您对壁纸有热情，欢迎加入我们的创作者社区，分享您的作品，获得积分和荣誉！</p>
            ''',
            'is_active': True,
        },
        {
            'config_type': 'privacy',
            'title': '隐私政策',
            'content': '''
<h2>隐私政策</h2>
<p>最后更新时间：2026年4月16日</p>

<p>我们非常重视您的隐私保护。本隐私政策说明了我们如何收集、使用、存储和保护您的个人信息。</p>

<h3>1. 信息收集</h3>
<p>我们可能收集以下信息：</p>
<ul>
    <li><strong>账户信息</strong>：注册时提供的邮箱、昵称等</li>
    <li><strong>使用数据</strong>：浏览记录、下载记录、收藏记录等</li>
    <li><strong>设备信息</strong>：设备类型、操作系统、浏览器类型等</li>
    <li><strong>上传内容</strong>：您上传的壁纸及相关资料</li>
</ul>

<h3>2. 信息使用</h3>
<p>我们使用收集的信息用于：</p>
<ul>
    <li>提供和改进我们的服务</li>
    <li>个性化推荐壁纸</li>
    <li>发送重要通知（如系统维护、功能更新）</li>
    <li>防止欺诈和滥用行为</li>
    <li>遵守法律法规要求</li>
</ul>

<h3>3. 信息共享</h3>
<p>我们不会向第三方出售或出租您的个人信息。仅在以下情况下可能共享信息：</p>
<ul>
    <li>经您明确同意</li>
    <li>为遵守法律义务或响应司法程序</li>
    <li>保护我们的权利、财产或安全</li>
</ul>

<h3>4. 信息安全</h3>
<p>我们采取合理的技术和管理措施保护您的个人信息，包括：</p>
<ul>
    <li>数据加密传输（HTTPS）</li>
    <li>密码加密存储</li>
    <li>定期安全审计</li>
    <li>访问权限控制</li>
</ul>

<h3>5. 您的权利</h3>
<p>您有权：</p>
<ul>
    <li>访问、更正或删除您的个人信息</li>
    <li>撤回同意（不影响撤回前的处理活动）</li>
    <li>注销账户</li>
    <li>投诉和举报</li>
</ul>

<h3>6. 联系我们</h3>
<p>如果您对本隐私政策有任何疑问，请联系：privacy@example.com</p>
            ''',
            'is_active': True,
        },
        {
            'config_type': 'terms',
            'title': '服务条款',
            'content': '''
<h2>服务条款</h2>
<p>最后更新时间：2026年4月16日</p>

<p>欢迎使用我们的服务！在使用我们的服务之前，请仔细阅读以下条款。</p>

<h3>1. 接受条款</h3>
<p>通过访问或使用我们的服务，即表示您同意受本服务条款的约束。如果您不同意这些条款，请不要使用我们的服务。</p>

<h3>2. 服务内容</h3>
<p>我们提供壁纸浏览、下载、上传、收藏等服务。我们有权随时修改、暂停或终止部分或全部服务。</p>

<h3>3. 用户账户</h3>
<ul>
    <li>您需要提供准确、完整的注册信息</li>
    <li>您有责任保管好账户密码</li>
    <li>如发现账户被盗用，请立即通知我们</li>
    <li>我们有权暂停或终止违反条款的账户</li>
</ul>

<h3>4. 用户上传内容</h3>
<ul>
    <li>您必须拥有上传内容的版权或已获得授权</li>
    <li>不得上传违法、色情、暴力等内容</li>
    <li>我们有权审核、删除违规内容</li>
    <li>上传即表示授予我们展示、分发的权利</li>
</ul>

<h3>5. 知识产权</h3>
<ul>
    <li>平台的所有内容（除用户上传外）归我们所有</li>
    <li>用户保留其上传内容的版权</li>
    <li>未经授权使用他人内容可能导致账户被封禁</li>
</ul>

<h3>6. 免责声明</h3>
<ul>
    <li>我们不保证服务的连续性、及时性、安全性</li>
    <li>对于因使用服务导致的损失，我们不承担责任</li>
    <li>用户应自行判断下载内容的安全性</li>
</ul>

<h3>7. 条款修改</h3>
<p>我们有权随时修改本条款，修改后的条款将在网站上公布。继续使用服务即表示接受修改后的条款。</p>

<h3>8. 联系方式</h3>
<p>如有问题，请联系：legal@example.com</p>
            ''',
            'is_active': True,
        },
    ]
    
    for config_data in configs:
        config, created = SiteConfig.objects.update_or_create(
            config_type=config_data['config_type'],
            defaults=config_data
        )
        status = "创建" if created else "更新"
        print(f"{status}成功：{config.get_config_type_display()}")
    
    print("\n✅ 所有配置初始化完成！")


if __name__ == '__main__':
    init_site_config()
