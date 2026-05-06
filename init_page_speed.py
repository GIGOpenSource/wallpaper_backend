# -*- coding: UTF-8 -*-
"""
页面速度功能使用说明
"""

"""
## 功能说明

页面速度管理功能已创建完成，包含以下功能：

### 1. 数据模型 (PageSpeed)
- page_path: 页面路径（如 /markwallpapers/search）
- full_url: 完整URL（自动拼接网站前缀）
- overall_score: 综合评分（0-100）
- lcp: 最大内容绘制时间（秒）
- fid: 首次输入延迟（毫秒）
- cls: 累积布局偏移
- load_time: 加载时间（秒）
- page_size: 页面大小（KB）
- issue_count: 问题数

### 2. API接口

#### 基础CRUD接口
- GET /api/seo/page_speed/ - 获取页面速度列表
- GET /api/seo/page_speed/{id}/ - 获取详情
- POST /api/seo/page_speed/ - 创建记录（自动测试）
- PUT /api/seo/page_speed/{id}/ - 更新记录
- PATCH /api/seo/page_speed/{id}/ - 部分更新
- DELETE /api/seo/page_speed/{id}/ - 删除记录

#### 特殊接口
- POST /api/seo/page_speed/test/ - 测试新页面
  请求体: {"page_path": "/markwallpapers/search"}
  
- GET /api/seo/page_speed/statistics/ - 获取统计信息

### 3. 筛选参数
列表接口支持以下筛选参数：
- min_score: 最小综合评分
- max_score: 最大综合评分
- min_issues: 最小问题数
- max_issues: 最大问题数
- page_path: 页面路径模糊匹配

### 4. 配置说明

#### Google PageSpeed Insights API配置
要使用真实的PageSpeed API，需要在 settings/pro.py 中添加：

```python
PAGESPEED_API_KEY = 'your_google_pagespeed_api_key'
```

获取API密钥步骤：
1. 访问 https://console.cloud.google.com/
2. 创建项目或选择现有项目
3. 启用 "PageSpeed Insights API"
4. 创建API密钥
5. 将密钥添加到配置文件

如果不配置API密钥，系统会使用模拟数据进行测试。

#### 网站前缀配置
网站前缀默认从 SiteConfig 表中读取（config_type='basic_settings'）。
如果没有配置，默认使用: https://www.markwallpapers.com

可以在后台管理系统中配置网站基础设置来修改前缀。

### 5. 使用示例

#### 测试新页面
```bash
curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"page_path": "/markwallpapers/search"}'
```

响应示例：
```json
{
  "code": 201,
  "data": {
    "id": 1,
    "page_path": "/markwallpapers/search",
    "full_url": "https://www.markwallpapers.com/markwallpapers/search",
    "overall_score": 85,
    "lcp": 2.5,
    "fid": 50.0,
    "cls": 0.1,
    "load_time": 3.2,
    "page_size": 1500.5,
    "issue_count": 3,
    "tested_at": "2026-05-06T10:00:00Z",
    "created_at": "2026-05-06T10:00:00Z",
    "remark": null
  },
  "message": "页面速度测试成功"
}
```

#### 获取列表
```bash
curl -X GET "http://localhost:8000/api/seo/page_speed/?min_score=70&page_path=search" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 获取统计信息
```bash
curl -X GET http://localhost:8000/api/seo/page_speed/statistics/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

响应示例：
```json
{
  "code": 200,
  "data": {
    "total_count": 10,
    "avg_score": 78.5,
    "excellent_count": 3,
    "needs_improvement_count": 2
  },
  "message": "统计信息获取成功"
}
```

### 6. 数据库迁移

运行以下命令创建数据库表：
```bash
python manage.py makemigrations models
python manage.py migrate models
```

### 7. 注意事项

1. 所有接口都需要管理员权限（IsAdmin）
2. 创建记录时会自动调用PageSpeed API进行测试
3. 如果同一页面路径已存在，会更新现有记录而不是创建新记录
4. 测试接口（/test/）专门用于快速测试新页面
5. 建议定期运行测试以更新页面性能数据
"""

print(__doc__)
