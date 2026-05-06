# 页面速度平台支持 - 快速参考

## 🚀 快速开始

### 1. 数据库迁移
```bash
python manage.py makemigrations models
python manage.py migrate models
```

### 2. 测试接口

#### 测试桌面端（默认）
```bash
POST /api/seo/page_speed/test/
{"page_path": "/markwallpapers/search"}
```

#### 测试手机端
```bash
POST /api/seo/page_speed/test/
{"page_path": "/markwallpapers/search", "platform": "phone"}
```

#### 测试平板端
```bash
POST /api/seo/page_speed/test/
{"page_path": "/markwallpapers/search", "platform": "pad"}
```

---

## 📋 API速查表

### 测试页面
```
POST /api/seo/page_speed/test/
Body: {"page_path": "路径", "platform": "page|phone|pad"}
```

### 获取列表
```
GET /api/seo/page_speed/?platform=phone
返回: 简化格式 (page_path, platform, mobile_friendly, overall_score, load_time)

GET /api/seo/page_speed/?platform=page  
返回: 完整格式 (所有字段)
```

### 筛选参数
- `platform`: page | phone | pad
- `mobile_friendly`: friendly | unfriendly
- `min_score`: 最小评分
- `max_score`: 最大评分
- `page_path`: 路径模糊搜索

### 统计数据
```
GET /api/seo/page_speed/statistics/?platform=phone
```

---

## 🎯 核心概念

### 平台类型
| 值 | 说明 | 测试策略 |
|----|------|---------|
| page | 桌面端 | desktop |
| phone | 手机 | mobile |
| pad | 平板 | mobile |

### 移动友好性
| 值 | 说明 | 适用平台 |
|----|------|---------|
| friendly | 友好 | phone, pad |
| unfriendly | 不友好 | phone, pad |
| null | 无数据 | page |

---

## 💡 常用场景

### 场景1: 对比多平台性能
```bash
# 分别测试三个平台
curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Authorization: Bearer TOKEN" \
  -d '{"page_path": "/search", "platform": "page"}'

curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Authorization: Bearer TOKEN" \
  -d '{"page_path": "/search", "platform": "phone"}'

curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Authorization: Bearer TOKEN" \
  -d '{"page_path": "/search", "platform": "pad"}'
```

### 场景2: 查找移动不友好页面
```bash
GET /api/seo/page_speed/?platform=phone&mobile_friendly=unfriendly
```

### 场景3: 查看各平台统计
```bash
# 桌面端
GET /api/seo/page_speed/statistics/?platform=page

# 手机端
GET /api/seo/page_speed/statistics/?platform=phone

# 平板端
GET /api/seo/page_speed/statistics/?platform=pad
```

---

## 📊 返回数据示例

### 移动端简化格式
```json
{
  "id": 1,
  "page_path": "/search",
  "platform": "phone",
  "platform_display": "手机",
  "mobile_friendly": "friendly",
  "mobile_friendly_display": "友好",
  "overall_score": 75,
  "load_time": 3.5
}
```

### 桌面端完整格式
```json
{
  "id": 2,
  "page_path": "/search",
  "platform": "page",
  "platform_display": "桌面端",
  "full_url": "https://www.markwallpapers.com/search",
  "overall_score": 85,
  "mobile_friendly": null,
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
```

---

## ⚠️ 注意事项

1. ✅ 不传 `platform` 默认为 `page`
2. ✅ 同一路径+平台只能有一条记录
3. ✅ 移动友好性仅移动端有值
4. ✅ 移动端列表返回简化格式
5. ✅ 完全向后兼容原有功能

---

## 🔗 相关文档

- 详细文档: `PageSpeed平台支持更新说明.md`
- 完成总结: `PageSpeed平台支持完成总结.md`
- 测试脚本: `test_page_speed_platform.py`

---

**就这么简单！** 🎉
