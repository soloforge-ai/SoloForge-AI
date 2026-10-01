"""Dedicated SoloForge Content Factory background worker runtime.

This process owns the long-running polling loops that must not depend on
FastAPI web traffic. It intentionally reuses the existing job/state machine
and Supabase-backed queue semantics.
"""

from __future__ import annotations

import asyncio
import signal

from backend.audio_generation import audio_worker_loop
from backend.content_asset_generation import content_asset_worker_loop
from backend.content_generation import content_worker_loop
from backend.content_router import content_router_loop
from backend.final_render import final_render_worker_loop
from backend.publora_publishing import publishing_worker_loop


WORKERS = (
    ("content_generation", content_worker_loop),
    ("content_router", content_router_loop),
    ("content_asset", content_asset_worker_loop),
    ("audio", audio_worker_loop),
    ("final_render", final_render_worker_loop),
    ("publishing", publishing_worker_loop),
)


async def run_background_workers() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_shutdown() -> None:
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, request_shutdown)
        except NotImplementedError:
            pass

    tasks = [
        asyncio.create_task(worker(), name=name)
        for name, worker in WORKERS
    ]

    try:
        await stop_event.wait()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def main() -> None:
    asyncio.run(run_background_workers())


if __name__ == "__main__":
    main()
