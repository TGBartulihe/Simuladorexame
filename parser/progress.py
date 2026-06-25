from __future__ import annotations

import time
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    TextColumn,
)

console = Console()


@contextmanager
def progress_bar(total: int, description: str):

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
        console=console,
    )

    task = progress.add_task(description, total=total)

    progress.start()

    try:
        yield progress, task

    finally:
        progress.stop()


class Stopwatch:

    def __init__(self):

        self.start = time.perf_counter()

    @property
    def elapsed(self):

        return time.perf_counter() - self.start