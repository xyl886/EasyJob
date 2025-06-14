import threading
from collections import defaultdict


class FileLockManager:
    _lock_map = defaultdict(threading.Lock)
    _global_lock = threading.Lock()  # 用于保护 _lock_map 的并发访问

    @classmethod
    def get_lock(cls, file_path: str) -> threading.Lock:
        with cls._global_lock:  # 保护字典操作
            if file_path not in cls._lock_map:
                cls._lock_map[file_path] = threading.Lock()
            return cls._lock_map[file_path]
