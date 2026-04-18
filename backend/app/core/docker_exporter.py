"""Gnosis Docker Exporter — generate Dockerfile and docker-compose for agents."""

from datetime import datetime, timezone


class DockerExporter:
    """Generates Docker artifacts for agent deployment."""

    def __init__(self):
        self._exports: dict[str, dict] = {}

    def generate_dockerfile(self, agent_config: dict) -> str:
        agent_name = agent_config.get("name", "gnosis-agent")
        python_version = agent_config.get("python_version", "3.11")
        return f"""FROM python:{python_version}-slim
LABEL maintainer="gnosis" agent="{agent_name}"

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV AGENT_NAME="{agent_name}"
ENV GNOSIS_MODE="standalone"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

    def generate_compose(self, agent_config: dict) -> str:
        agent_name = agent_config.get("name", "gnosis-agent")
        port = agent_config.get("port", 8000)
        return f"""version: "3.8"

services:
  {agent_name}:
    build: .
    container_name: {agent_name}
    ports:
      - "{port}:8000"
    environment:
      - AGENT_NAME={agent_name}
      - GNOSIS_MODE=standalone
      - LOG_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
"""

    def export_agent(self, agent_id: str, agent_config: dict) -> dict:
        dockerfile = self.generate_dockerfile(agent_config)
        compose = self.generate_compose(agent_config)
        result = {
            "agent_id": agent_id,
            "dockerfile": dockerfile,
            "docker_compose": compose,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        self._exports[agent_id] = result
        return result


docker_exporter = DockerExporter()
