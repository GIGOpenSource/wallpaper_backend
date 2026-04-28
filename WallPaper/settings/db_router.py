class AppDBRouter:
    """
    数据库路由适配：
    - 老库（old_db）：仅读取后台 User，禁止写入/迁移
    - 新库（default）：客户与壁纸等模型的读写+迁移
    """
    # 老库只读的模型（小写，匹配 Django 内部 model_name）
    OLD_DB_READ_ONLY_MODELS = [
        'models.user'
    ]

    def db_for_read(self, model, **hints):
        """读取规则：老库模型读 old_db，其他读 default"""
        model_path = f"{model._meta.app_label}.{model.__name__.lower()}"
        if model_path in self.OLD_DB_READ_ONLY_MODELS:
            return 'old_db'  # 老库模型只读 old_db
        return 'default'     # 其他模型读新库

    def db_for_write(self, model, **hints):
        """写入规则：禁止写入老库模型，所有写入都到新库"""
        model_path = f"{model._meta.app_label}.{model.__name__.lower()}"
        if model_path in self.OLD_DB_READ_ONLY_MODELS:
            return 'old_db'  # 返回 None 禁止写入老库（抛出错误，防止误写）
            # return None  # 迁移时使用
        return 'default'  # 其他模型写入新库

    def allow_relation(self, obj1, obj2, **hints):
        """关联规则：仅允许同库内关联"""
        # 老库模型之间允许关联
        if obj1._state.db == 'old_db' and obj2._state.db == 'old_db':
            return True
        # 新库模型之间允许关联
        elif obj1._state.db == 'default' and obj2._state.db == 'default':
            return True
        # 跨库关联禁止
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """迁移规则：
        - 老库（old_db）：禁止所有迁移（只读）
        - 新库（default）：仅迁移新库模型，禁止迁移老库模型
        """
        full_model_name = f"{app_label}.{model_name}" if model_name else None
        print(f"迁移检测：模型={full_model_name}，目标数据库={db}")

        # 老库禁止任何迁移
        if db == 'old_db':
            print(f"old_db 库禁止迁移：{full_model_name}")
            return False

        # 新库：仅允许迁移新库模型，禁止迁移老库模型
        if db == 'default':
            # 老库模型禁止在新库迁移
            if full_model_name in self.OLD_DB_READ_ONLY_MODELS:
                print(f"新库禁止迁移老库模型：{full_model_name}")
                return False
            # 新库模型允许迁移
            # result = full_model_name in self.NEW_DB_MODELS
            print(f"新库迁移允许：{full_model_name}")
            return True
        # 其他数据库禁止迁移
        return False