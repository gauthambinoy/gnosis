from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Counters
REQUEST_COUNT = Counter('gnosis_http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
AGENT_EXECUTIONS = Counter('gnosis_agent_executions_total', 'Total agent executions', ['status'])
LLM_REQUESTS = Counter('gnosis_llm_requests_total', 'Total LLM API calls', ['provider', 'tier'])
MEMORY_OPERATIONS = Counter('gnosis_memory_ops_total', 'Memory operations', ['operation', 'tier'])
AUTH_EVENTS = Counter('gnosis_auth_events_total', 'Auth events', ['event'])

# Business metrics — agent executions with agent_id label
AGENT_EXEC_DETAILED = Counter('gnosis_agent_exec_detailed_total', 'Agent executions by agent', ['agent_id', 'status'])
LLM_REQUESTS_BY_MODEL = Counter('gnosis_llm_requests_by_model_total', 'LLM requests by model', ['model', 'tier'])
LLM_COST_USD = Counter('gnosis_llm_cost_usd', 'Estimated LLM cost in USD', ['model'])
AGENT_CORRECTION = Counter('gnosis_agent_correction_total', 'Agent self-corrections')

# Histograms
REQUEST_LATENCY = Histogram('gnosis_http_request_duration_seconds', 'Request latency', ['method', 'endpoint'],
                            buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10])
EXECUTION_LATENCY = Histogram('gnosis_execution_duration_seconds', 'Agent execution latency',
                              buckets=[0.1, 0.5, 1, 5, 10, 30, 60])
LLM_LATENCY = Histogram('gnosis_llm_request_duration_seconds', 'LLM request latency', ['provider'])

# Queue metrics
TASK_QUEUE_DEPTH = Gauge('gnosis_task_queue_depth', 'Total tasks pending in queue')
TASK_PROCESSING_DURATION = Histogram('gnosis_task_processing_duration_seconds', 'Task processing duration',
                                     buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120, 300])

# Gauges
ACTIVE_AGENTS = Gauge('gnosis_active_agents', 'Number of active agents')
ACTIVE_CONNECTIONS = Gauge('gnosis_active_ws_connections', 'Active WebSocket connections')
MEMORY_VECTORS = Gauge('gnosis_memory_vectors_total', 'Total memory vectors stored')
CACHE_SIZE = Gauge('gnosis_cache_entries', 'Cache entries', ['cache_type'])
TASK_WORKER_TASKS = Gauge('gnosis_task_worker_registered', 'Registered background tasks')

# Info
APP_INFO = Info('gnosis', 'Gnosis application info')
APP_INFO.info({'version': '1.0.0', 'name': 'Gnosis'})

class MetricsMiddleware(BaseHTTPMiddleware):
    """Automatically track request count + latency for all endpoints."""
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        # Normalize path (replace UUIDs with {id})
        path = request.url.path
        import re
        path = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '{id}', path)
        
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        
        REQUEST_COUNT.labels(method=method, endpoint=path, status=response.status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)
        
        return response

def metrics_endpoint(request: Request) -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
