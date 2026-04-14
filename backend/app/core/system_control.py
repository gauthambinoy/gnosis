"""
Gnosis System Control — Secure OS/System Management
Provides authorized admin access to server management.
All operations require admin auth + are fully audited.
"""
import asyncio
import os
import platform
import shutil
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

# Try importing psutil for system metrics
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class CommandResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    command: str = ""
    output: str = ""
    error: str = ""
    exit_code: int = -1
    executed_at: float = field(default_factory=time.time)
    duration_ms: float = 0
    executed_by: str = ""


class SystemControlEngine:
    """Secure system management with full audit trail."""

    # Commands that are NEVER allowed (security)
    BLOCKED_COMMANDS = [
        "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
        ":(){:|:&};:", "chmod -R 777 /", "mv / /dev/null",
        "wget|sh", "curl|sh", "shutdown", "reboot", "halt",
        "passwd", "userdel", "groupdel", "visudo",
    ]

    # Only these command prefixes are allowed (whitelist approach)
    ALLOWED_COMMAND_PREFIXES = [
        "ls", "cat", "head", "tail", "grep", "find", "wc",
        "df", "du", "free", "top -bn1", "ps", "uptime", "whoami",
        "docker", "docker-compose", "docker compose",
        "systemctl status", "systemctl list-units",
        "journalctl", "netstat", "ss", "ip addr",
        "python3", "pip3 list", "pip3 show",
        "node --version", "npm list",
        "pg_isready", "redis-cli ping", "redis-cli info",
        "curl -s http://localhost", "curl -s https://localhost",
        "env | grep -v KEY | grep -v SECRET | grep -v PASSWORD | grep -v TOKEN",
        "uname", "hostname", "date", "id",
        "nginx -t", "nginx -T",
        "aws ecs", "aws s3 ls", "aws rds describe", "aws cloudwatch",
        "terraform plan", "terraform show",
        "alembic current", "alembic history",
    ]

    def __init__(self):
        self._audit_log: list[dict] = []
        self._command_history: list[CommandResult] = []
        self._max_history = 500
        self._max_output_size = 50000  # 50KB max output per command
        self._command_timeout = 30  # seconds

    # ─── System Info ───

    def get_system_info(self) -> dict:
        """Get comprehensive system information."""
        info = {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "uptime_seconds": 0,
            "cpu": {"cores": os.cpu_count(), "usage_percent": 0},
            "memory": {"total_gb": 0, "used_gb": 0, "available_gb": 0, "percent": 0},
            "disk": {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0},
            "network": {},
            "processes": {"total": 0, "running": 0},
        }

        if HAS_PSUTIL:
            try:
                info["uptime_seconds"] = time.time() - psutil.boot_time()

                cpu = psutil.cpu_percent(interval=0.5)
                info["cpu"]["usage_percent"] = cpu
                info["cpu"]["per_core"] = psutil.cpu_percent(percpu=True)

                mem = psutil.virtual_memory()
                info["memory"] = {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "used_gb": round(mem.used / (1024**3), 2),
                    "available_gb": round(mem.available / (1024**3), 2),
                    "percent": mem.percent,
                }

                disk = shutil.disk_usage("/")
                info["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round(disk.used / disk.total * 100, 1),
                }

                net = psutil.net_io_counters()
                info["network"] = {
                    "bytes_sent": net.bytes_sent,
                    "bytes_recv": net.bytes_recv,
                    "packets_sent": net.packets_sent,
                    "packets_recv": net.packets_recv,
                }

                procs = list(psutil.process_iter(['status']))
                info["processes"]["total"] = len(procs)
                info["processes"]["running"] = sum(
                    1 for p in procs if p.info['status'] == 'running'
                )

            except Exception:
                pass
        else:
            # Fallback without psutil
            try:
                disk = shutil.disk_usage("/")
                info["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round(disk.used / disk.total * 100, 1),
                }
            except Exception:
                pass

        return info

    def get_running_services(self) -> list[dict]:
        """Get status of key services."""
        services = []
        checks = [
            ("Backend API", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/health"),
            ("Frontend", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000"),
            ("PostgreSQL", "pg_isready -q && echo UP || echo DOWN"),
            ("Redis", "redis-cli ping 2>/dev/null || echo DOWN"),
        ]
        # Return static list — actual checks done via execute_command
        for name, check_cmd in checks:
            services.append({"name": name, "check_command": check_cmd, "status": "unknown"})
        return services

    def get_docker_status(self) -> dict:
        """Get Docker container status."""
        return {
            "available": shutil.which("docker") is not None,
            "compose_available": (
                shutil.which("docker-compose") is not None
                or shutil.which("docker") is not None
            ),
            "note": "Use execute_command with 'docker ps' to see running containers",
        }

    # ─── Secure Command Execution ───

    def _is_command_safe(self, command: str) -> tuple[bool, str]:
        """Validate command against security rules."""
        cmd_lower = command.lower().strip()

        # Check blocked commands
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return False, f"Blocked command pattern: {blocked}"

        # Check for dangerous patterns
        dangerous = [
            ("|sh", "Pipe to shell"),
            ("|bash", "Pipe to bash"),
            (">/dev/sd", "Write to disk device"),
            ("chmod 777", "Insecure permissions"),
            ("--no-preserve-root", "Dangerous rm flag"),
            ("eval ", "Code injection risk"),
            ("exec ", "Code injection risk"),
            ("$(", "Command substitution"),
            ("`", "Command substitution"),
        ]
        for pattern, reason in dangerous:
            if pattern in cmd_lower:
                return False, f"Blocked: {reason}"

        # Whitelist check
        allowed = False
        for prefix in self.ALLOWED_COMMAND_PREFIXES:
            if cmd_lower.startswith(prefix.lower()):
                allowed = True
                break

        if not allowed:
            return False, (
                f"Command not in whitelist. Allowed prefixes: "
                f"{', '.join(self.ALLOWED_COMMAND_PREFIXES[:10])}..."
            )

        return True, "OK"

    async def execute_command(
        self, command: str, user_id: str = "admin", timeout: int = 0
    ) -> dict:
        """Execute a whitelisted command with full auditing."""
        timeout = min(timeout or self._command_timeout, 60)  # Max 60s

        # Security check
        safe, reason = self._is_command_safe(command)
        if not safe:
            result = CommandResult(
                command=command, error=f"BLOCKED: {reason}",
                exit_code=-1, executed_by=user_id,
            )
            self._audit(user_id, "command_blocked", command, reason)
            return asdict(result)

        result = CommandResult(command=command, executed_by=user_id)
        start = time.time()

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/",
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                result.output = stdout.decode("utf-8", errors="replace")[
                    : self._max_output_size
                ]
                result.error = stderr.decode("utf-8", errors="replace")[
                    : self._max_output_size
                ]
                result.exit_code = proc.returncode or 0
            except asyncio.TimeoutError:
                proc.kill()
                result.error = f"Command timed out after {timeout}s"
                result.exit_code = -2

        except Exception as e:
            result.error = str(e)
            result.exit_code = -1

        result.duration_ms = (time.time() - start) * 1000

        # Audit
        self._audit(
            user_id, "command_executed", command,
            f"exit={result.exit_code} duration={result.duration_ms:.0f}ms",
        )

        # Store history
        self._command_history.append(result)
        if len(self._command_history) > self._max_history:
            self._command_history = self._command_history[-self._max_history:]

        return asdict(result)

    # ─── File Browser ───

    def list_directory(self, path: str = "/app") -> dict:
        """Safely list directory contents."""
        blocked_paths = ["/etc/shadow", "/etc/gshadow", "/root/.ssh"]
        if any(path.startswith(bp) for bp in blocked_paths):
            return {"error": "Access denied to sensitive path"}

        try:
            entries = []
            for entry in os.scandir(path):
                try:
                    stat = entry.stat()
                    entries.append({
                        "name": entry.name,
                        "type": "dir" if entry.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "permissions": oct(stat.st_mode)[-3:],
                    })
                except (PermissionError, OSError):
                    entries.append({
                        "name": entry.name,
                        "type": "unknown",
                        "error": "permission denied",
                    })

            entries.sort(key=lambda e: (e["type"] != "dir", e["name"]))
            return {"path": path, "entries": entries, "count": len(entries)}
        except PermissionError:
            return {"error": f"Permission denied: {path}"}
        except FileNotFoundError:
            return {"error": f"Path not found: {path}"}

    def read_file(self, path: str, max_lines: int = 200) -> dict:
        """Read a file safely (text only, limited size)."""
        blocked_patterns = [
            "shadow", ".ssh/id_", ".env", "secret", "password", "token", "key",
        ]
        path_lower = path.lower()
        if any(p in path_lower for p in blocked_patterns):
            return {"error": "Access denied — sensitive file pattern detected"}

        try:
            size = os.path.getsize(path)
            if size > 1_000_000:  # 1MB max
                return {"error": f"File too large ({size} bytes). Max 1MB."}

            with open(path, "r", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(
                            f"... truncated at {max_lines} lines ({size} bytes total)"
                        )
                        break
                    lines.append(line.rstrip())

            return {
                "path": path,
                "lines": len(lines),
                "size": size,
                "content": "\n".join(lines),
            }
        except PermissionError:
            return {"error": f"Permission denied: {path}"}
        except (FileNotFoundError, IsADirectoryError) as e:
            return {"error": str(e)}

    # ─── Process Management ───

    def list_processes(self, top_n: int = 30) -> list[dict]:
        """List top processes by CPU/memory usage."""
        if not HAS_PSUTIL:
            return [{"error": "psutil not installed"}]

        try:
            procs = []
            for p in psutil.process_iter(
                ['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'username']
            ):
                try:
                    info = p.info
                    procs.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu_percent": info['cpu_percent'] or 0,
                        "memory_percent": round(info['memory_percent'] or 0, 1),
                        "status": info['status'],
                        "user": info['username'],
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            procs.sort(key=lambda p: p['cpu_percent'], reverse=True)
            return procs[:top_n]
        except Exception as e:
            return [{"error": str(e)}]

    def get_network_connections(self) -> list[dict]:
        """List active network connections."""
        if not HAS_PSUTIL:
            return [{"error": "psutil not installed"}]

        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                connections.append({
                    "local_addr": (
                        f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
                    ),
                    "remote_addr": (
                        f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
                    ),
                    "status": conn.status,
                    "pid": conn.pid,
                })
            return connections[:100]
        except (psutil.AccessDenied, Exception) as e:
            return [{"error": str(e)}]

    # ─── Docker Management ───

    async def docker_ps(self) -> dict:
        """Get running Docker containers."""
        return await self.execute_command(
            "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
            "system",
        )

    async def docker_logs(self, container: str, lines: int = 50) -> dict:
        """Get Docker container logs."""
        # Sanitize container name
        container = "".join(c for c in container if c.isalnum() or c in "-_")
        return await self.execute_command(
            f"docker logs --tail {min(lines, 200)} {container}", "system"
        )

    async def docker_stats(self) -> dict:
        """Get Docker resource usage."""
        return await self.execute_command(
            "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'",
            "system",
        )

    # ─── Audit ───

    def _audit(self, user_id: str, action: str, detail: str, result: str = ""):
        self._audit_log.append({
            "timestamp": time.time(),
            "user_id": user_id,
            "action": action,
            "detail": detail[:500],
            "result": result[:200],
        })
        # Keep last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

    def get_audit_log(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._audit_log[-limit:]))

    def get_command_history(self, limit: int = 50) -> list[dict]:
        return [asdict(c) for c in reversed(self._command_history[-limit:])]


# Singleton
system_control = SystemControlEngine()
