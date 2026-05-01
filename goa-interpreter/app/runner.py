from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from loguru import logger

from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask

from app.config import Settings
from app.pipeline import build_pipeline_task
from app.sessions import Session


@dataclass
class _SessionRun:
    task: PipelineTask
    runner_task: asyncio.Task


@dataclass
class PipelineManager:
    _runs: dict[str, _SessionRun] = field(default_factory=dict)

    async def start(self, settings: Settings, session: Session) -> None:
        if session.id in self._runs:
            logger.warning("session={} already running", session.id)
            return

        task = build_pipeline_task(settings, session)
        runner = PipelineRunner(handle_sigint=False)

        async def _run() -> None:
            try:
                await runner.run(task)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("session={} pipeline crashed", session.id)
            finally:
                self._runs.pop(session.id, None)
                logger.info("session={} pipeline exited", session.id)

        runner_task = asyncio.create_task(_run(), name=f"pipeline-{session.id}")
        self._runs[session.id] = _SessionRun(task=task, runner_task=runner_task)
        logger.info("session={} pipeline started", session.id)

    async def stop(self, session_id: str) -> None:
        run = self._runs.get(session_id)
        if not run:
            return
        await run.task.cancel()
        try:
            await asyncio.wait_for(run.runner_task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            run.runner_task.cancel()
        self._runs.pop(session_id, None)


manager = PipelineManager()
