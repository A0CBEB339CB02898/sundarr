from dataclasses import dataclass, field
from typing import Any, BinaryIO

from sundarr.app.storage.base import StorageWriter


@dataclass(frozen=True)
class SmbConfig:
    host: str
    share: str
    username: str
    password: str | None = None
    port: int = 445
    domain: str = ""
    base_path: str = "/"
    libraries: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SmbConfig":
        return cls(
            host=str(value.get("host", "")),
            share=str(value.get("share", "")),
            username=str(value.get("username", "")),
            password=value.get("password"),
            port=int(value.get("port", 445)),
            domain=str(value.get("domain", "")),
            base_path=str(value.get("base_path", "/")),
            libraries={str(key): str(item) for key, item in value.get("libraries", {}).items()},
        )


class SmbWriter(StorageWriter):
    name = "smb"

    def __init__(self, config: SmbConfig) -> None:
        self.config = config
        self._base_parts = self._safe_parts(config.base_path)

    async def exists(self, path: str) -> bool:
        smbclient = self._require_smbclient()
        try:
            return smbclient.path.exists(self._build_unc_path(path))
        except Exception as exc:
            raise ValueError("SMB_CONNECT_FAILED") from exc

    async def size(self, path: str) -> int:
        smbclient = self._require_smbclient()
        target = self._build_unc_path(path)
        try:
            if not smbclient.path.exists(target):
                raise ValueError("STORAGE_PATH_NOT_FOUND")
            return int(smbclient.stat(target).st_size)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("SMB_CONNECT_FAILED") from exc

    async def mkdirs(self, path: str) -> None:
        smbclient = self._require_smbclient()
        try:
            smbclient.makedirs(self._build_unc_path(path), exist_ok=True)
        except Exception as exc:
            raise ValueError("SMB_WRITE_FAILED") from exc

    async def open_append(self, path: str) -> BinaryIO:
        smbclient = self._require_smbclient()
        target = self._build_unc_path(path)
        parent = target.rsplit("\\", 1)[0]
        try:
            smbclient.makedirs(parent, exist_ok=True)
            return smbclient.open_file(target, mode="ab")
        except Exception as exc:
            raise ValueError("SMB_WRITE_FAILED") from exc

    async def rename(self, src: str, dst: str) -> None:
        smbclient = self._require_smbclient()
        source = self._build_unc_path(src)
        target = self._build_unc_path(dst)
        try:
            if smbclient.path.exists(target):
                raise ValueError("TARGET_EXISTS")
            smbclient.rename(source, target)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("SMB_RENAME_FAILED") from exc

    async def remove(self, path: str) -> None:
        smbclient = self._require_smbclient()
        parts = self._safe_parts(path)
        if not parts:
            raise ValueError("STORAGE_REMOVE_ROOT_FORBIDDEN")
        target = self._build_unc_path(path)
        try:
            if smbclient.path.isdir(target):
                smbclient.rmdir(target)
            elif smbclient.path.exists(target):
                smbclient.remove(target)
        except Exception as exc:
            raise ValueError("SMB_WRITE_FAILED") from exc

    async def list_dir(self, path: str) -> list[dict[str, object]]:
        target = self._build_unc_path(path)
        smbclient = self._require_smbclient()
        entries: list[dict[str, object]] = []
        try:
            for entry in smbclient.scandir(target):
                child_path = "/".join([*self._safe_parts(path), entry.name])
                entries.append(
                    {
                        "name": entry.name,
                        "path": child_path,
                        "is_dir": entry.is_dir(),
                        "size": None if entry.is_dir() else int(entry.stat().st_size),
                    }
                )
        except Exception as exc:
            raise ValueError("SMB_CONNECT_FAILED") from exc
        return entries

    async def test_connection(self) -> None:
        smbclient = self._require_smbclient()
        try:
            smbclient.listdir(self._build_unc_path(""))
        except Exception as exc:
            raise ValueError("SMB_CONNECT_FAILED") from exc

    def _build_unc_path(self, path: str) -> str:
        parts = [*self._base_parts, *self._safe_parts(path)]
        suffix = "\\".join(parts)
        root = f"\\\\{self.config.host}\\{self.config.share}"
        return f"{root}\\{suffix}" if suffix else root

    def _safe_parts(self, path: str) -> list[str]:
        normalized = path.strip().replace("\\", "/").strip("/")
        if not normalized:
            return []
        parts = [part for part in normalized.split("/") if part]
        if any(part == ".." for part in parts):
            raise ValueError("SMB_PATH_OUTSIDE_ROOT")
        if normalized.startswith("//") or ":" in normalized:
            raise ValueError("SMB_PATH_INVALID")
        return parts

    def _require_smbclient(self):
        try:
            import smbclient  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError("SMB_CLIENT_NOT_INSTALLED") from exc
        try:
            self._register_session(smbclient)
        except Exception as exc:
            raise ValueError("SMB_CONNECT_FAILED") from exc
        return smbclient

    def _register_session(self, smbclient) -> None:
        username = f"{self.config.domain}\\{self.config.username}" if self.config.domain else self.config.username
        smbclient.register_session(
            self.config.host,
            username=username,
            password=self.config.password or "",
            port=self.config.port,
        )
