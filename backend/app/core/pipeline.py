"""Gnosis Pipeline Engine — Chain agents together for multi-step workflows."""
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger("gnosis.pipeline")


class PipelineStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStep:
    id: str
    agent_id: str
    name: str
    order: int
    transform_input: Optional[str] = None  # Jinja-like template to transform output->input
    condition: Optional[str] = None  # Simple condition: "output.status == 'success'"
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 1


@dataclass
class StepResult:
    step_id: str
    status: StepStatus
    output: dict = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass 
class Pipeline:
    id: str
    name: str
    description: str = ""
    steps: List[PipelineStep] = field(default_factory=list)
    status: PipelineStatus = PipelineStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: Optional[str] = None


@dataclass
class PipelineRun:
    id: str
    pipeline_id: str
    status: PipelineStatus
    initial_input: dict = field(default_factory=dict)
    step_results: List[StepResult] = field(default_factory=list)
    current_step: int = 0
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    total_duration_ms: float = 0


class PipelineEngine:
    """Manages pipeline CRUD and execution."""
    
    def __init__(self):
        self._pipelines: Dict[str, Pipeline] = {}
        self._runs: Dict[str, PipelineRun] = {}
        self._execute_agent_fn = None  # Will be set from outside
    
    def set_executor(self, fn):
        """Set the agent execution function."""
        self._execute_agent_fn = fn
    
    def _validate_agent_id(self, agent_id: str) -> bool:
        """Validate that an agent_id refers to an existing agent."""
        try:
            from app.core.marketplace import marketplace_engine
            agent = marketplace_engine.get_agent(agent_id)
            return agent is not None
        except Exception:
            # If we can't check, allow it (don't block pipeline creation)
            return True
    
    # ── CRUD ─────────────────────────────────────────────────────
    
    def create_pipeline(self, name: str, description: str = "", steps: list = None, created_by: str = None) -> Pipeline:
        pipeline = Pipeline(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_by=created_by,
        )
        if steps:
            for i, step_data in enumerate(steps):
                agent_id = step_data["agent_id"]
                if not self._validate_agent_id(agent_id):
                    raise ValueError(f"Pipeline step references non-existent agent: {agent_id}")
                step = PipelineStep(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    name=step_data.get("name", f"Step {i+1}"),
                    order=i,
                    transform_input=step_data.get("transform_input"),
                    condition=step_data.get("condition"),
                    timeout_seconds=step_data.get("timeout_seconds", 300),
                    max_retries=step_data.get("max_retries", 1),
                )
                pipeline.steps.append(step)
        self._pipelines[pipeline.id] = pipeline
        logger.info(f"Pipeline created: {pipeline.id} with {len(pipeline.steps)} steps")
        return pipeline
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        return self._pipelines.get(pipeline_id)
    
    def list_pipelines(self) -> List[Pipeline]:
        return sorted(self._pipelines.values(), key=lambda p: p.created_at, reverse=True)
    
    def update_pipeline(self, pipeline_id: str, **kwargs) -> Optional[Pipeline]:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None
        for key, value in kwargs.items():
            if hasattr(pipeline, key) and key not in ('id', 'created_at'):
                setattr(pipeline, key, value)
        pipeline.updated_at = datetime.now(timezone.utc).isoformat()
        return pipeline
    
    def delete_pipeline(self, pipeline_id: str) -> bool:
        return self._pipelines.pop(pipeline_id, None) is not None
    
    def add_step(self, pipeline_id: str, agent_id: str, name: str, **kwargs) -> Optional[PipelineStep]:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None
        if not self._validate_agent_id(agent_id):
            raise ValueError(f"Pipeline step references non-existent agent: {agent_id}")
        step = PipelineStep(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            name=name,
            order=len(pipeline.steps),
            **kwargs,
        )
        pipeline.steps.append(step)
        return step
    
    def remove_step(self, pipeline_id: str, step_id: str) -> bool:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return False
        pipeline.steps = [s for s in pipeline.steps if s.id != step_id]
        # Re-order
        for i, step in enumerate(pipeline.steps):
            step.order = i
        return True
    
    # ── Execution ────────────────────────────────────────────────
    
    async def execute(self, pipeline_id: str, initial_input: dict = None) -> PipelineRun:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        
        if not pipeline.steps:
            raise ValueError("Pipeline has no steps")
        
        run = PipelineRun(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline_id,
            status=PipelineStatus.RUNNING,
            initial_input=initial_input or {},
        )
        self._runs[run.id] = run
        
        # Execute steps sequentially
        current_output = initial_input or {}
        sorted_steps = sorted(pipeline.steps, key=lambda s: s.order)
        
        for i, step in enumerate(sorted_steps):
            run.current_step = i
            step_result = StepResult(
                step_id=step.id,
                status=StepStatus.RUNNING,
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            
            try:
                # Check condition
                if step.condition and not self._evaluate_condition(step.condition, current_output):
                    step_result.status = StepStatus.SKIPPED
                    step_result.completed_at = datetime.now(timezone.utc).isoformat()
                    run.step_results.append(step_result)
                    continue
                
                # Transform input
                step_input = self._transform_input(step.transform_input, current_output) if step.transform_input else current_output
                
                # Execute agent with retries
                import time
                start = time.time()
                result = await self._execute_with_retry(step, step_input)
                step_result.duration_ms = (time.time() - start) * 1000
                
                step_result.status = StepStatus.COMPLETED
                step_result.output = result
                step_result.completed_at = datetime.now(timezone.utc).isoformat()
                current_output = result  # Feed output to next step
                
            except Exception as e:
                step_result.status = StepStatus.FAILED
                step_result.error = str(e)
                step_result.completed_at = datetime.now(timezone.utc).isoformat()
                run.step_results.append(step_result)
                run.status = PipelineStatus.FAILED
                run.completed_at = datetime.now(timezone.utc).isoformat()
                logger.error(f"Pipeline {pipeline_id} failed at step {i}: {e}")
                return run
            
            run.step_results.append(step_result)
        
        run.status = PipelineStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc).isoformat()
        run.total_duration_ms = sum(r.duration_ms for r in run.step_results)
        logger.info(f"Pipeline {pipeline_id} completed in {run.total_duration_ms:.1f}ms")
        return run
    
    async def _execute_with_retry(self, step: PipelineStep, input_data: dict) -> dict:
        last_error = None
        for attempt in range(step.max_retries + 1):
            try:
                if self._execute_agent_fn:
                    result = await asyncio.wait_for(
                        self._execute_agent_fn(step.agent_id, input_data),
                        timeout=step.timeout_seconds,
                    )
                    return result if isinstance(result, dict) else {"output": str(result)}
                else:
                    return {"output": f"[dry-run] Step '{step.name}' executed with input: {list(input_data.keys())}"}
            except Exception as e:
                last_error = e
                step.retry_count = attempt + 1
                if attempt < step.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        raise last_error or RuntimeError("Step execution failed")
    
    def _evaluate_condition(self, condition: str, output: dict) -> bool:
        """Simple condition evaluation. Only supports basic checks."""
        try:
            # Support: "output.key == 'value'" and "output.key != 'value'"
            if "==" in condition:
                parts = condition.split("==")
                key = parts[0].strip().replace("output.", "")
                value = parts[1].strip().strip("'\"")
                return str(output.get(key, "")) == value
            if "!=" in condition:
                parts = condition.split("!=")
                key = parts[0].strip().replace("output.", "")
                value = parts[1].strip().strip("'\"")
                return str(output.get(key, "")) != value
            return True
        except Exception:
            return True
    
    def _transform_input(self, template: str, output: dict) -> dict:
        """Simple input transformation using {{key}} syntax."""
        import re
        result = {}
        for match in re.finditer(r'(\w+)\s*=\s*\{\{(\w+)\}\}', template):
            target_key, source_key = match.group(1), match.group(2)
            result[target_key] = output.get(source_key, "")
        return result if result else output
    
    # ── Run history ──────────────────────────────────────────────
    
    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        return self._runs.get(run_id)
    
    def list_runs(self, pipeline_id: str = None) -> List[PipelineRun]:
        runs = list(self._runs.values())
        if pipeline_id:
            runs = [r for r in runs if r.pipeline_id == pipeline_id]
        return sorted(runs, key=lambda r: r.started_at, reverse=True)
    
    @property
    def stats(self) -> dict:
        return {
            "total_pipelines": len(self._pipelines),
            "total_runs": len(self._runs),
            "completed_runs": sum(1 for r in self._runs.values() if r.status == PipelineStatus.COMPLETED),
            "failed_runs": sum(1 for r in self._runs.values() if r.status == PipelineStatus.FAILED),
        }


pipeline_engine = PipelineEngine()
