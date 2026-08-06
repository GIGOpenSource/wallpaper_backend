# WallPaper 项目配置流程

适用仓库：`C:\Users\l'l\wallpaper`（Django + DRF）

> 不要按通用教程配 MySQL / 本机 Redis。本项目用远程 PostgreSQL + 远程 Redis。

---

## 配置步骤总览

| 步骤 | 内容 | 状态参考 |
|------|------|----------|
| **第 1 步** | 创建虚拟环境 | 必须 |
| **第 2 步** | 安装依赖 `req.txt` | 必须 |
| **第 3 步** | 配置 `.env` | 必须 |
| **第 4 步** | **配置 IDE 解释器 + 运行/调试** | **必须（你问的这一步）** |
| **第 5 步** | `manage.py check` 检查 | 必须 |
| **第 6 步** | 启动服务 / 调试 | 必须 |
| **第 7 步** | 验证登录注册 | 建议 |

---

## 第 1 步：创建虚拟环境

```powershell
cd C:\Users\l'l\wallpaper
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
```

解释器路径（后面第 4 步要用）：

```text
C:\Users\l'l\wallpaper\.venv\Scripts\python.exe
```

---

## 第 2 步：安装依赖

```powershell
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r req.txt
```

或阿里云镜像：

```powershell
pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r req.txt
```

验证：

```powershell
python -c "import django, rest_framework; print(django.get_version())"
```

---

## 第 3 步：配置 `.env`

项目根目录 `.env` 中 Redis 至少包含：

```env
REDIS_HOST=101.32.179.223
REDIS_PORT=6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=20
REDIS_PASSWORD="Redis@2026#0119"
```

注意：密码含 `#`，**必须加双引号**。不要用 `127.0.0.1:6379`。

数据库在 `WallPaper/settings/pro.py`，一般无需在 `.env` 再配 PostgreSQL。

---

## 第 4 步：配置 IDE 解释器 + 运行/调试（本步）

在依赖装好、`.env` 配好之后，**启动项目前**做这一步，让 IDE 用对虚拟环境里的 Python。

### PyCharm

1. **设置解释器**  
   `文件` → `设置` → `项目` → `Python 解释器`  
   → 选择已有解释器，或添加：  
   `C:\Users\l'l\wallpaper\.venv\Scripts\python.exe`

2. **编辑运行/调试配置**（运行按钮旁下拉 → `编辑配置…`）

| 项 | 填写值 |
|----|--------|
| 名称 | `wallpaper` 或 `Django` |
| 脚本路径 | `C:\Users\l'l\wallpaper\manage.py` |
| 参数 | `runserver 0.0.0.0:8000` |
| 工作目录 | `C:\Users\l'l\wallpaper` |
| Python 解释器 | 选第 1 点配置的 `.venv` |
| 环境变量 | 见下方 |

建议环境变量：

```text
PYTHONUNBUFFERED=1;DJANGO_SETTINGS_MODULE=WallPaper.settings.pro
```

3. 点 **确定** 保存。  
4. 日常：绿色三角 = 运行；虫子图标 = 调试（可命中断点）。

### Cursor / VS Code

1. `Ctrl+Shift+P` → `Python: Select Interpreter`  
   → 选 `.venv\Scripts\python.exe`
2. 可选：`.vscode/launch.json` 增加 Django 调试配置：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Django",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/manage.py",
      "args": ["runserver", "0.0.0.0:8000"],
      "django": true,
      "env": {
        "DJANGO_SETTINGS_MODULE": "WallPaper.settings.pro"
      }
    }
  ]
}
```

---

## 第 5 步：环境检查

```powershell
python manage.py check
```

期望：

- `Redis连接成功！地址：101.32.179.223:6379`
- `System check identified no issues`

---

## 第 6 步：启动

**方式 A：终端**

```powershell
python manage.py runserver 0.0.0.0:8000
```

**方式 B：IDE**  
使用第 4 步配好的配置，点运行或调试。

- 文档：http://127.0.0.1:8000/api/docs/  
- 访问 `/` 出现 404 正常（纯 API，无首页）

---

## 第 7 步：验证登录注册

### C 端客户

| 操作 | 方法 | URL |
|------|------|-----|
| 注册 | POST | `/api/client/users/register/` |
| 登录 | POST | `/api/client/users/login/` |
| 资料 | GET | `/api/client/users/profile/` |

登录后请求头必须是：

```text
token: <完整token>
```

不要用 `Authorization`。

### 管理员

| 操作 | URL |
|------|-----|
| 注册 | POST `/api/users/register/` |
| 登录 | POST `/api/users/login/` |

---

## 常见问题

| 现象 | 处理 |
|------|------|
| pip SSL 失败 | 换源或加 `--trusted-host` |
| Redis 连不上 localhost | 改用 `.env` 远程地址 |
| Redis 密码错误 | 密码加引号包住 `#` |
| profile 401 | Header 用 `token` |
| 解释器选错 | 第 4 步改回 `.venv` 路径 |
| 跟错项目 | 确认有 `App/`、`WallPaper/`、`manage.py` |

---

## 与截图配置的对应关系

若 PyCharm「编辑运行/调试配置」里类似：

- 脚本路径 → `...\wallpaper\manage.py`
- 参数 → `runserver`
- 解释器 → `...\venv` 或 `...\ .venv\Scripts\python.exe`
- 工作目录 → 项目根目录

则这些都写在 **第 4 步**。本仓库推荐使用 `.venv`，并补上：

```text
DJANGO_SETTINGS_MODULE=WallPaper.settings.pro
```
