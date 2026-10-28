"""OS-owned process lock. A crashed process releases it automatically."""
from pathlib import Path
import os

class ProcessLock:
    def __init__(self,path:Path):self.path=Path(path);self.handle=None
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.handle=self.path.open('a+b')
        self.handle.seek(0);self.handle.write(b'0');self.handle.flush();self.handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,BlockingIOError) as exc:
            self.handle.close();self.handle=None
            raise RuntimeError(f'Another service owns {self.path.name}') from exc
        return self
    def release(self):
        if self.handle:
            self.handle.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
            self.handle.close();self.handle=None
    def __enter__(self):return self.acquire()
    def __exit__(self,*args):self.release()
