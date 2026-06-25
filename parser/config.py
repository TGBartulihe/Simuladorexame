from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:

    project_name: str = "SimuladorExame"

    database: Path = ROOT / "database" / "simuladorexame.db"

    storage: Path = ROOT / "storage"

    pdf_directory: Path = ROOT / "storage" / "pdfs"

    cache_directory: Path = ROOT / "cache"

    log_directory: Path = ROOT / "logs"

    export_directory: Path = ROOT / "exports"

    temp_directory: Path = ROOT / "temp"

    ollama_url: str = os.getenv(
        "OLLAMA_URL",
        "http://localhost:11434/api/generate"
    )

    ollama_model: str = os.getenv(
        "OLLAMA_MODEL",
        "qwen2.5:7b"
    )

    log_level: str = os.getenv(
        "LOG_LEVEL",
        "INFO"
    )

    parser_version: str = "2.0.0"

    prompt_version: str = "1.0.0"

    max_workers: int = 4

    save_every: int = 1

    progress_refresh: float = 0.2

    resume_processing: bool = True

    overwrite_existing: bool = False


CONFIG = Config()


def ensure_directories() -> None:

    CONFIG.storage.mkdir(parents=True, exist_ok=True)

    CONFIG.pdf_directory.mkdir(parents=True, exist_ok=True)

    CONFIG.cache_directory.mkdir(parents=True, exist_ok=True)

    CONFIG.log_directory.mkdir(parents=True, exist_ok=True)

    CONFIG.export_directory.mkdir(parents=True, exist_ok=True)

    CONFIG.temp_directory.mkdir(parents=True, exist_ok=True)