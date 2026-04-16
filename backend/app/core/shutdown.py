"""Graceful shutdown handler for Gnosis."""
import asyncio
import signal
from typing import Set, Optional
from app.core.logger import get_logger

logger = get_logger("shutdown")


class ShutdownManager:
    def __init__(self, drain_timeout: float = 30.0):
        self._shutting_down = False
        self._active_tasks: Set[asyncio.Task] = set()
        self._drain_timeout = drain_timeout
        self._shutdown_event = asyncio.Event()

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    def register_task(self, task: asyncio.Task):
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    async def shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info(f"shutdown_initiated active_tasks={len(self._active_tasks)}")

        if self._active_tasks:
            logger.info(
                f"draining_tasks count={len(self._active_tasks)} "
                f"timeout={self._drain_timeout}"
            )
            done, pending = await asyncio.wait(
                self._active_tasks, timeout=self._drain_timeout
            )
            if pending:
                logger.warning(f"force_cancelling_tasks count={len(pending)}")
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
            logger.info(
                f"drain_complete completed={len(done)} cancelled={len(pending)}"
            )

        self._shutdown_event.set()
        logger.info("shutdown_complete")

    def install_signal_handlers(
        self, loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        loop = loop or asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._handle_signal(s)),
            )

    async def _handle_signal(self, sig):
        logger.info(f"signal_received signal={sig.name}")
        await self.shutdown()


shutdown_manager = ShutdownManager()
