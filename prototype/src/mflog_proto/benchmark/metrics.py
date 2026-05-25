"""Environment metadata collection for benchmark reports."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import importlib.util
import platform
import sys
from typing import Any


DEPENDENCIES = ("pytest", "numpy", "polars", "PySide6", "pyqtgraph", "psutil", "yaml")


@dataclass(frozen=True)
class DependencyInfo:
    name: str
    available: bool
    version: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "version": self.version,
        }


@dataclass(frozen=True)
class EnvironmentInfo:
    python_version: str
    platform: str
    machine: str
    processor: str
    dependencies: dict[str, DependencyInfo]

    def to_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "machine": self.machine,
            "processor": self.processor,
            "dependencies": {
                name: info.to_dict() for name, info in self.dependencies.items()
            },
        }


def collect_environment() -> EnvironmentInfo:
    return EnvironmentInfo(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        dependencies={name: _dependency_info(name) for name in DEPENDENCIES},
    )


def _dependency_info(name: str) -> DependencyInfo:
    available = importlib.util.find_spec(name) is not None
    version = None
    if available:
        package_name = "PyYAML" if name == "yaml" else name
        try:
            version = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            version = None
    return DependencyInfo(name=name, available=available, version=version)

