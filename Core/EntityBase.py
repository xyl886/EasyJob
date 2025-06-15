import threading


class EntityBase:
    """实体基类（线程安全版）"""

    _tls = threading.local()


    def __init__(self, **kwargs):
        # 安全地获取当前线程的 job 上下文
        current_job = getattr(EntityBase._tls, 'current_job', None)

        # 设置默认值
        self.RunId = kwargs.get('RunId')
        self.RunDate = kwargs.get('RunDate')
        self.InsertUpdateTime = kwargs.get('InsertUpdateTime')

        # 优先使用上下文中的值
        if current_job:
            self.RunId = current_job.run_id
            self.RunDate = current_job.date
            self.InsertUpdateTime = current_job.InsertUpdateTime

    @classmethod
    def get_current_job(cls):
        """线程安全获取当前任务实例"""
        return getattr(cls._tls, 'current_job', None)

    @classmethod
    def set_current_job(cls, job):
        """线程安全设置当前任务实例"""
        cls._tls.current_job = job

    def dict(self):
        """返回实例属性的字典表示（排除类属性）"""
        return {**self.__dict__}  # 或 return vars(self).copy()
