# 页面速度管理功能

## 概述

页面速度管理功能用于监控和管理网站各页面的性能指标，基于 Google PageSpeed Insights API 提供详细的性能分析数据。

## 功能特性

### 1. 核心指标
- **综合评分 (overall_score)**: 0-100分的整体性能评分
- **LCP (Largest Contentful Paint)**: 最大内容绘制时间，衡量加载性能
- **FID (First Input Delay)**: 首次输入延迟，衡量交互性
- **CLS (Cumulative Layout Shift)**: 累积布局偏移，衡量视觉稳定性
- **加载时间 (load_time)**: 页面完全加载所需时间
- **页面大小 (page_size)**: 页面总资源大小（KB）
- **问题数 (issue_count)**: 需要优化的问题数量

### 2. 自动化测试
- 创建记录时自动调用PageSpeed API进行测试
- 支持手动触发页面测试
- 自动拼接网站前缀生成完整URL

### 3. 智能筛选
- 按评分范围筛选
- 按问题数筛选
- 按页面路径模糊搜索

### 4. 统计分析
- 总页面数统计
- 平均评分计算
- 优秀页面识别（评分≥90）
- 待优化页面识别（评分<70）

## 文件结构

```
App/view/seo/page_speed/
├── __init__.py          # 模块初始化
├── view.py              # 视图层（CRUD接口）
├── tools.py             # 工具层（API调用）
└── urls.py              # 路由配置

models/
└── models.py            # PageSpeed模型（已添加）
```

## API接口文档

### 基础URL
```
/api/seo/page_speed/
```

### 1. 获取页面速度列表

**请求**
```http
GET /api/seo/page_speed/?min_score=70&max_score=90&page_path=search
```

**查询参数**
- `min_score`: 最小综合评分（可选）
- `max_score`: 最大综合评分（可选）
- `min_issues`: 最小问题数（可选）
- `max_issues`: 最大问题数（可选）
- `page_path`: 页面路径模糊匹配（可选）

**响应**
```json
{
  "code": 200,
  "data": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 10,
      "total_pages": 1
    },
    "results": [
      {
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
      }
    ]
  },
  "message": "列表获取成功"
}
```

### 2. 获取页面速度详情

**请求**
```http
GET /api/seo/page_speed/1/
```

**响应**
```json
{
  "code": 200,
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
  "message": "详情获取成功"
}
```

### 3. 创建页面速度记录（自动测试）

**请求**
```http
POST /api/seo/page_speed/
Content-Type: application/json

{
  "page_path": "/markwallpapers/search",
  "remark": "首页搜索结果页"
}
```

**响应**
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
    "remark": "首页搜索结果页"
  },
  "message": "页面速度测试并保存成功"
}
```

### 4. 更新页面速度记录

**请求**
```http
PUT /api/seo/page_speed/1/
Content-Type: application/json

{
  "page_path": "/markwallpapers/search",
  "remark": "更新后的备注"
}
```

**响应**
```json
{
  "code": 200,
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
    "remark": "更新后的备注"
  },
  "message": "更新成功"
}
```

### 5. 部分更新

**请求**
```http
PATCH /api/seo/page_speed/1/
Content-Type: application/json

{
  "remark": "只更新备注"
}
```

### 6. 删除页面速度记录

**请求**
```http
DELETE /api/seo/page_speed/1/
```

**响应**
```json
{
  "code": 200,
  "message": "删除成功"
}
```

### 7. 测试新页面（专用接口）

**请求**
```http
POST /api/seo/page_speed/test/
Content-Type: application/json

{
  "page_path": "/markwallpapers/search"
}
```

**说明**
- 此接口专门用于快速测试新页面
- 会自动调用PageSpeed API进行测试
- 如果页面已存在则更新，不存在则创建
- 返回完整的测试结果

**响应**
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

### 8. 获取统计信息

**请求**
```http
GET /api/seo/page_speed/statistics/
```

**响应**
```json
{
  "code": 200,
  "data": {
    "total_count": 50,
    "avg_score": 78.5,
    "excellent_count": 15,
    "needs_improvement_count": 8
  },
  "message": "统计信息获取成功"
}
```

## 配置说明

### 1. Google PageSpeed Insights API配置

在 `WallPaper/settings/pro.py` 中添加：

```python
# Google PageSpeed Insights API密钥
PAGESPEED_API_KEY = 'your_api_key_here'
```

**获取API密钥步骤：**
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目或选择现有项目
3. 启用 "PageSpeed Insights API"
4. 创建API密钥
5. 将密钥添加到配置文件

**注意：** 如果不配置API密钥，系统会使用模拟数据进行测试。

### 2. 网站前缀配置

网站前缀默认从 `SiteConfig` 表中读取（`config_type='basic_settings'`）。

**配置方式：**
- 通过后台管理系统配置网站基础设置
- 在 `config_value` JSON字段中设置 `site_url`

**默认值：** `https://www.markwallpapers.com`

## 数据库迁移

运行以下命令创建数据库表：

```bash
# 生成迁移文件
python manage.py makemigrations models

# 执行迁移
python manage.py migrate models
```

## 测试

### 运行测试脚本

```bash
python test_page_speed.py
```

测试内容包括：
1. 网站前缀获取测试
2. 页面速度扫描测试
3. 数据库操作测试
4. 统计功能测试

### API测试示例

使用curl测试：

```bash
# 测试新页面
curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"page_path": "/markwallpapers/search"}'

# 获取列表
curl -X GET "http://localhost:8000/api/seo/page_speed/?min_score=70" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 获取统计
curl -X GET http://localhost:8000/api/seo/page_speed/statistics/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 使用场景

### 1. 新页面性能监控
当开发新页面时，使用 `/test/` 接口快速测试性能：
```bash
POST /api/seo/page_speed/test/
{"page_path": "/new-feature/page"}
```

### 2. 定期性能审计
遍历所有重要页面，批量测试：
```python
pages = ["/", "/search", "/detail/123", ...]
for page in pages:
    requests.post(f"{BASE_URL}/test/", json={"page_path": page})
```

### 3. 性能优化跟踪
通过筛选低分页面，优先优化：
```bash
GET /api/seo/page_speed/?max_score=70
```

### 4. 性能趋势分析
定期记录统计数据，分析性能变化趋势。

## 注意事项

1. **权限要求**: 所有接口都需要管理员权限（IsAdmin）
2. **重复处理**: 同一页面路径会更新现有记录而非创建新记录
3. **API限制**: Google PageSpeed API有配额限制，合理使用
4. **测试频率**: 建议定期测试以获取最新性能数据
5. **模拟数据**: 未配置API密钥时使用模拟数据，仅供测试

## 性能指标说明

### LCP (Largest Contentful Paint)
- **优秀**: ≤ 2.5秒
- **一般**: 2.5-4.0秒
- **较差**: > 4.0秒

### FID (First Input Delay)
- **优秀**: ≤ 100毫秒
- **一般**: 100-300毫秒
- **较差**: > 300毫秒

### CLS (Cumulative Layout Shift)
- **优秀**: ≤ 0.1
- **一般**: 0.1-0.25
- **较差**: > 0.25

### 综合评分
- **优秀**: ≥ 90
- **良好**: 70-89
- **待优化**: < 70

## 常见问题

### Q: 为什么测试结果是模拟数据？
A: 检查是否配置了 `PAGESPEED_API_KEY`，未配置时会使用模拟数据。

### Q: 如何修改网站前缀？
A: 在后台管理系统的网站配置中修改 `basic_settings` 的 `site_url` 字段。

### Q: 测试失败怎么办？
A: 检查网络连接、API密钥是否正确，查看日志获取详细错误信息。

### Q: 可以测试本地开发环境吗？
A: 可以，但需要确保URL可公开访问，或使用ngrok等工具暴露本地服务。

## 技术支持

如有问题，请查看：
- Django日志: `logs/` 目录
- Google PageSpeed API文档: https://developers.google.com/speed/docs/insights/v5/reference/pagespeedapi/runpagespeed
