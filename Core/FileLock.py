import random
import threading
import time
from collections import defaultdict
from concurrent.futures.thread import ThreadPoolExecutor


class FileLock:
    _lock_map = defaultdict(threading.Lock)
    _global_lock = threading.Lock()  # 用于保护 _lock_map 的并发访问

    @classmethod
    def get_lock(cls, file_path: str) -> threading.Lock:
        with cls._global_lock:  # 保护字典操作
            if file_path not in cls._lock_map:
                cls._lock_map[file_path] = threading.Lock()
            return cls._lock_map[file_path]


def file_access(file_path: str, thread_id: int):
    lock = FileLock.get_lock(file_path)
    with lock:
        if thread_id % 2 == 0:
            # 模拟文件操作前的准备
            start_msg = f"Thread {thread_id} started writing to {file_path}"
            print(start_msg)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(start_msg + "\n")
        else:
            end_msg = f"Thread {thread_id} finished writing to {file_path}"
            print(end_msg)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(end_msg + "\n")
    time.sleep(random.uniform(1, 2.5))


# 主测试函数
def main():
    file_paths = ["file1.txt",  "file2.txt", "file3.txt"]
    with ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(1,31):
            file_path = random.choice(file_paths)
            executor.submit(file_access, file_path, i)



if __name__ == "__main__":
    main()
