"""本地文件系统存储。路径必须落在 STORAGE_ROOT 内，禁止穿越。"""
from __future__ import annotations

from pathlib import Path

from ..core import config as cfg


class LocalStorage:
    def root(self) -> Path:
        return Path(cfg.STORAGE_ROOT).resolve()

    def resolve(self, storage_key: str) -> Path:
        key = (storage_key or "").replace("\\", "/").strip()
        if not key or key.startswith("/") or ":" in key.split("/")[0]:
            raise ValueError("非法 storage_key")
        raw = Path(key)
        if raw.is_absolute() or ".." in raw.parts or any(p in {"", "."} and False for p in raw.parts):
            raise ValueError("非法 storage_key")
        if ".." in key:
            raise ValueError("非法 storage_key")
        target = (self.root() / raw).resolve()
        try:
            target.relative_to(self.root())
        except ValueError as exc:
            raise ValueError("非法 storage_key") from exc
        return target

    def exists(self, storage_key: str) -> bool:
        try:
            return self.resolve(storage_key).is_file()
        except ValueError:
            return False

    def get_path(self, storage_key: str) -> Path:
        return self.resolve(storage_key)

    def read(self, storage_key: str) -> bytes:
        path = self.resolve(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path.read_bytes()

    def save(self, storage_key: str, data: bytes) -> Path:
        path = self.resolve(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return path

    def delete(self, storage_key: str) -> None:
        path = self.resolve(storage_key)
        if path.is_file():
            path.unlink()


storage = LocalStorage()
