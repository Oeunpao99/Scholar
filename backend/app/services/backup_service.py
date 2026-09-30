"""Database backup and restore helpers (pg_dump / pg_restore)."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import ROLE_ORDER, Role, has_at_least
from app.models.enums import AuditAction
from app.models.user import User

logger = logging.getLogger("scholar.backup")

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(slots=True)
class BackupInfo:
    filename: str
    size_bytes: int
    created_at: str
    format: str

    @property
    def size_display(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"


class BackupService:
    """Creates timestamped dumps and restores them through pg_restore."""

    def __init__(self, current_user: User | None = None) -> None:
        self.current_user = current_user

    # ---------------------------------------------------------------- create
    async def create(self, fmt: str = "custom", *, compress: bool = True) -> BackupInfo:
        if fmt not in {"custom", "plain", "tar", "directory"}:
            raise ValidationError("Backup format must be custom, plain, tar or directory.")
        extension = {"custom": "dump", "plain": "sql", "tar": "tar", "directory": "dir"}[fmt]
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = f"scholar_backup_{stamp}.{extension}"
        target = settings.BACKUP_DIR / name
        target.parent.mkdir(parents=True, exist_ok=True)

        await self._run_dump(fmt, target, compress)
        if not target.exists():
            raise AppError("pg_dump did not produce an output file.", status_code=500)

        stat = target.stat()
        await self._audit("backup", f"Created {fmt} backup {name} ({stat.st_size} bytes)")
        return BackupInfo(
            filename=name,
            size_bytes=stat.st_size,
            created_at=datetime.now(UTC).isoformat(),
            format=fmt,
        )

    # ----------------------------------------------------------------- list
    def list_backups(self) -> list[BackupInfo]:
        if not settings.BACKUP_DIR.exists():
            return []
        items: list[BackupInfo] = []
        for path in sorted(settings.BACKUP_DIR.glob("*"), reverse=True):
            if not path.is_file():
                continue
            stat = path.stat()
            suffix = path.suffix.lstrip(".")
            items.append(
                BackupInfo(
                    filename=path.name,
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    format={"dump": "custom", "sql": "plain", "tar": "tar"}.get(suffix, suffix),
                )
            )
        return items

    def resolve(self, filename: str) -> Path:
        safe = _SAFE_NAME.sub("", Path(filename).name)
        if not safe or safe != Path(filename).name:
            raise ValidationError("Invalid backup filename.")
        path = (settings.BACKUP_DIR / safe).resolve()
        if not str(path).startswith(str(settings.BACKUP_DIR.resolve())):
            raise ValidationError("Invalid backup path.")
        if not path.exists():
            raise NotFoundError(f"Backup '{safe}' was not found.")
        return path

    def read(self, filename: str) -> bytes:
        return self.resolve(filename).read_bytes()

    # -------------------------------------------------------------- restore
    async def restore(
        self, filename: str, *, clean: bool = True, actor: User | None = None
    ) -> dict[str, object]:
        if actor and not (actor.is_superuser or has_at_least(actor.role, Role.SUPERADMIN)):
            raise ValidationError("Restoring a database requires the superadmin role.")
        path = self.resolve(filename)
        fmt = {".dump": "custom", ".sql": "plain", ".tar": "tar"}.get(path.suffix, "custom")
        await self._run_restore(path, fmt, clean=clean)
        await self._audit("restore", f"Restored database from {path.name}", actor)
        return {"restored": True, "source": path.name, "format": fmt, "clean": clean}

    async def delete(self, filename: str, actor: User | None = None) -> bool:
        if actor and not (actor.is_superuser or has_at_least(actor.role, Role.SUPERADMIN)):
            raise ValidationError("Deleting backups requires the superadmin role.")
        path = self.resolve(filename)
        path.unlink()
        await self._audit("delete", f"Deleted backup {path.name}", actor)
        return True

    # -------------------------------------------------------------- internals
    async def _run_dump(self, fmt: str, target: Path, compress: bool) -> None:
        binary = shutil.which("pg_dump")
        if binary is None:
            raise AppError(
                "pg_dump is not available in this container. Use `docker compose exec db "
                "pg_dump` instead.",
                status_code=503,
                code="backup_unavailable",
            )
        command = [
            binary,
            "--host", settings.POSTGRES_SERVER or "localhost",
            "--port", str(settings.POSTGRES_PORT),
            "--username", settings.POSTGRES_USER,
            "--dbname", settings.POSTGRES_DB,
            "--format", fmt,
            "--no-owner",
            "--no-privileges",
            "--file", str(target),
        ]
        if compress and fmt == "plain":
            command.extend(["--compress", "5"])
        await self._exec(command)

    async def _run_restore(self, path: Path, fmt: str, *, clean: bool) -> None:
        binary = shutil.which("pg_restore") or shutil.which("psql")
        if binary is None:
            raise AppError(
                "pg_restore is not available in this container.",
                status_code=503,
                code="backup_unavailable",
            )
        command = [
            binary,
            "--host", settings.POSTGRES_SERVER or "localhost",
            "--port", str(settings.POSTGRES_PORT),
            "--username", settings.POSTGRES_USER,
            "--dbname", settings.POSTGRES_DB,
        ]
        if binary.endswith("pg_restore"):
            if clean:
                command.append("--clean")
                command.append("--if-exists")
            command.extend(["--no-owner", "--no-privileges", str(path)])
        else:
            command.extend(["-v", "ON_ERROR_STOP=1", "-f", str(path)])
        await self._exec(command)

    @staticmethod
    async def _exec(command: list[str]) -> None:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**_env_with_password()},
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error("Command failed: %s", " ".join(command))
            raise AppError(
                f"Backup command failed: {stderr.decode(errors='replace')[:500]}",
                status_code=500,
                code="backup_failed",
            )
        if stdout:
            logger.debug("Backup output: %s", stdout.decode(errors="replace")[:200])

    async def _audit(self, action: str, summary: str, actor: User | None = None) -> None:
        try:
            from app.db.session import SessionLocal
            from app.services.audit_service import AuditService

            async with SessionLocal() as session:
                await AuditService(session).log(
                    action=action,
                    entity_type="database",
                    summary=summary,
                    user=actor or self.current_user,
                )
                await session.commit()
        except Exception:  # noqa: BLE001 - auditing must never break the operation
            logger.warning("Could not write the backup audit entry", exc_info=True)


def _env_with_password() -> dict[str, str]:
    import os

    env = dict(os.environ)
    parsed = urlparse(settings.sync_database_url)
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    return env


__all__ = ["BackupService", "BackupInfo", "ROLE_ORDER"]
