import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def bundled_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", app_root())).resolve()


def bundled_path(*parts: str) -> Path:
    return bundled_root().joinpath(*parts)


def runtime_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def seed_runtime_knowledge() -> None:
    target_dir = runtime_path("knowledge")
    target_dir.mkdir(parents=True, exist_ok=True)
    if any(target_dir.iterdir()):
        return

    source_dir = bundled_path("knowledge")
    if not source_dir.exists():
        return

    for source in source_dir.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_dir)
        target = target_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
