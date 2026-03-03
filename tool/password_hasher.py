from passlib.context import CryptContext

# 配置加密上下文：使用 bcrypt 算法（安全性高，自动处理盐值）
# 支持自动识别旧密码哈希格式（便于后续算法升级）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw_password: str) -> str:
    """哈希密码（处理72字节限制）"""
    # 截断密码至72字节（bcrypt限制）
    truncated_bytes = raw_password.encode('utf-8')[:72]
    truncated_password = truncated_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(truncated_password)

def verify_password(raw_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # 同样截断原始密码进行验证
    truncated_password = raw_password[:72]
    return pwd_context.verify(truncated_password, hashed_password)