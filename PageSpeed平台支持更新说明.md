# 页面速度功能 - 平台/设备支持更新说明

## 更新概述

在原有页面速度检测功能基础上，新增了**平台/设备维度**支持，可以分别测试桌面端、手机端和平板端的页面性能。

## 主要更新内容

### 1. 数据模型更新

#### 新增字段
- **platform**: 平台类型
  - `page`: 桌面端（默认）
  - `phone`: 手机
  - `pad`: 平板
  
- **mobile_friendly**: 移动友好性（仅移动端有值）
  - `friendly`: 友好
  - `unfriendly`: 不友好
  - `null`: 桌面端或无数据

#### 索引优化
- 添加 `platform` 字段索引
- 添加 `mobile_friendly` 字段索引
- 添加联合唯一索引 `(page_path, platform)` - 同一页面路径+平台只能有一条记录

### 2. API接口更新

#### 测试新页面接口增强

**接口**: `POST /api/seo/page_speed/test/`

**请求参数**:
```json
{
  "page_path": "/markwallpapers/search",
  "platform": "phone"  // 可选，默认 page
}
```

**platform参数说明**:
- 不传或传 `page`: 测试桌面端
- 传 `phone`: 测试手机端
- 传 `pad`: 测试平板端

**响应示例** (手机端):
```json
{
  "code": 201,
  "data": {
    "id": 1,
    "page_path": "/markwallpapers/search",
    "platform": "phone",
    "platform_display": "手机",
    "full_url": "https://www.markwallpapers.com/markwallpapers/search",
    "overall_score": 75,
    "mobile_friendly": "friendly",
    "mobile_friendly_display": "友好",
    "lcp": 2.8,
    "fid": 45.0,
    "cls": 0.12,
    "load_time": 3.5,
    "page_size": 1800.5,
    "issue_count": 4,
    "tested_at": "2026-05-06T10:00:00Z",
    "created_at": "2026-05-06T10:00:00Z",
    "remark": null
  },
  "message": "页面速度测试成功"
}
```

#### 列表接口增强

**接口**: `GET /api/seo/page_speed/`

**新增查询参数**:
- `platform`: 按平台筛选 (page/phone/pad)
- `mobile_friendly`: 按移动友好性筛选 (friendly/unfriendly)

**移动端简化返回**:
当查询 `platform=phone` 或 `platform=pad` 时，返回简化格式：

```json
{
  "code": 200,
  "data": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 5,
      "total_pages": 1
    },
    "results": [
      {
        "id": 1,
        "page_path": "/markwallpapers/search",
        "platform": "phone",
        "platform_display": "手机",
        "mobile_friendly": "friendly",
        "mobile_friendly_display": "友好",
        "overall_score": 75,
        "load_time": 3.5
      }
    ]
  },
  "message": "列表获取成功"
}
```

**移动端返回字段说明**:
- `page_path`: 页面路径
- `platform`: 设备类型
- `platform_display`: 设备类型显示名称
- `mobile_friendly`: 移动友好性
- `mobile_friendly_display`: 移动友好性显示名称
- `overall_score`: 综合评分
- `load_time`: 加载时间

#### 统计接口增强

**接口**: `GET /api/seo/page_speed/statistics/`

**新增查询参数**:
- `platform`: 按平台统计 (page/phone/pad)

**使用示例**:
```bash
# 统计所有平台的整体数据
GET /api/seo/page_speed/statistics/

# 只统计手机端数据
GET /api/seo/page_speed/statistics/?platform=phone

# 只统计平板端数据
GET /api/seo/page_speed/statistics/?platform=pad
```

### 3. 技术实现

#### Google PageSpeed API策略
- **桌面端** (`page`): 使用 `strategy=desktop`
- **移动端** (`phone`, `pad`): 使用 `strategy=mobile`

#### 移动友好性检测
基于以下指标综合判断：
1. 视口配置 (viewport)
2. 字体大小 (font-size)
3. 触摸元素大小 (tap-targets)
4. 内容宽度 (content-width)

如果超过2个指标不合格，则判定为"不友好"。

#### 模拟数据逻辑
- 移动端评分通常比桌面端低5-10分
- 移动端加载时间通常比桌面端慢0.5秒
- 移动友好性基于评分判断：≥70分为友好，<70分为不友好

## 使用场景

### 场景1: 对比不同设备的性能

```bash
# 测试桌面端
curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"page_path": "/markwallpapers/search", "platform": "page"}'

# 测试手机端
curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"page_path": "/markwallpapers/search", "platform": "phone"}'

# 测试平板端
curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"page_path": "/markwallpapers/search", "platform": "pad"}'
```

### 场景2: 查看所有移动不友好的页面

```bash
GET /api/seo/page_speed/?platform=phone&mobile_friendly=unfriendly
```

### 场景3: 对比各平台平均性能

```bash
# 桌面端统计
GET /api/seo/page_speed/statistics/?platform=page

# 手机端统计
GET /api/seo/page_speed/statistics/?platform=phone

# 平板端统计
GET /api/seo/page_speed/statistics/?platform=pad
```

### 场景4: 批量测试多平台

```python
import requests

BASE_URL = "http://localhost:8000/api/seo/page_speed/test/"
TOKEN = "your_token"

pages = [
    "/",
    "/markwallpapers/search",
    "/markwallpapers/detail/123"
]

platforms = ["page", "phone", "pad"]

for page in pages:
    for platform in platforms:
        response = requests.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"page_path": page, "platform": platform}
        )
        print(f"{page} - {platform}: {response.json()['data']['overall_score']}")
```

## 数据库迁移

由于修改了模型结构，需要执行迁移：

```bash
# 生成迁移文件
python manage.py makemigrations models

# 执行迁移
python manage.py migrate models
```

**注意**: 
- 原有的 `page_path` 唯一约束被移除
- 新增 `(page_path, platform)` 联合唯一约束
- 如果已有数据，迁移会自动处理

## API兼容性

### 向后兼容
- 不传 `platform` 参数时，默认为 `page`（桌面端）
- 原有接口调用方式保持不变
- 原有数据自动标记为 `platform='page'`

### 新增功能
- 所有接口都支持 `platform` 参数
- 移动端列表返回简化格式
- 新增 `mobile_friendly` 相关字段

## 完整API示例

### 1. 测试不同平台

```bash
# 桌面端
POST /api/seo/page_speed/test/
{"page_path": "/search"}

# 手机端
POST /api/seo/page_speed/test/
{"page_path": "/search", "platform": "phone"}

# 平板端
POST /api/seo/page_speed/test/
{"page_path": "/search", "platform": "pad"}
```

### 2. 获取列表

```bash
# 获取所有桌面端数据
GET /api/seo/page_speed/?platform=page

# 获取所有手机端数据（简化格式）
GET /api/seo/page_speed/?platform=phone

# 获取移动不友好的页面
GET /api/seo/page_speed/?platform=phone&mobile_friendly=unfriendly

# 获取评分低于70的手机端页面
GET /api/seo/page_speed/?platform=phone&max_score=70
```

### 3. 获取统计

```bash
# 整体统计
GET /api/seo/page_speed/statistics/

# 手机端统计
GET /api/seo/page_speed/statistics/?platform=phone
```

## 注意事项

1. **唯一性约束**: 同一页面路径 + 平台组合只能有一条记录
2. **移动友好性**: 仅在手机端和平板端有值，桌面端为 null
3. **默认行为**: 不传 platform 参数时默认为 page（桌面端）
4. **返回列表**: 查询移动端时使用简化序列化器，减少数据传输量
5. **API密钥**: 建议使用真实的 PageSpeed API 密钥获取准确数据

## 总结

本次更新在不改变原有功能的基础上：
- ✅ 新增平台维度支持（桌面端/手机/平板）
- ✅ 新增移动友好性检测
- ✅ 优化移动端列表返回格式
- ✅ 支持按平台筛选和统计
- ✅ 完全向后兼容

现在可以更全面地监控和优化网站在不同设备上的性能表现！
