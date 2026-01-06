"""
kubectl-service: Executes kubectl and helm commands against a Kubernetes cluster.
Kubeconfig is mounted at /root/.kube/config
"""

import subprocess
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(
    title="K8s Command Service",
    description="Execute kubectl and helm commands against a Kubernetes cluster",
    version="1.0.0"
)

# Allowed command prefixes for security
ALLOWED_COMMANDS = ["kubectl", "helm"]


class KubectlRequest(BaseModel):
    """Request to execute a kubectl command."""
    command: str = Field(..., description="kubectl command arguments (e.g., 'get pods -n default')")
    timeout: int = Field(default=30, ge=1, le=300, description="Command timeout in seconds")


class CommandRequest(BaseModel):
    """Request to execute a kubectl or helm command."""
    command: str = Field(..., description="Full command with tool prefix (e.g., 'kubectl get pods' or 'helm list')")
    timeout: int = Field(default=60, ge=1, le=600, description="Command timeout in seconds")


class KubectlResponse(BaseModel):
    """Response from kubectl command execution."""
    stdout: str
    stderr: str
    return_code: int
    command: str
    execution_time_ms: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    kubectl_version: Optional[str] = None
    helm_version: Optional[str] = None
    kubeconfig_found: bool


def get_kubectl_version() -> Optional[str]:
    """Get kubectl client version."""
    try:
        result = subprocess.run(
            ["kubectl", "version", "--client", "--short"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_helm_version() -> Optional[str]:
    """Get helm client version."""
    try:
        result = subprocess.run(
            ["helm", "version", "--short"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def check_kubeconfig() -> bool:
    """Check if kubeconfig exists and is readable."""
    try:
        result = subprocess.run(
            ["kubectl", "config", "current-context"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    kubectl_version = get_kubectl_version()
    helm_version = get_helm_version()
    kubeconfig_found = check_kubeconfig()

    return HealthResponse(
        status="healthy" if kubectl_version and helm_version else "degraded",
        service="kubectl-service",
        kubectl_version=kubectl_version,
        helm_version=helm_version,
        kubeconfig_found=kubeconfig_found
    )


@app.post("/execute", response_model=KubectlResponse)
async def execute_kubectl(request: KubectlRequest):
    """
    Execute a kubectl command.

    The command should be the arguments to kubectl (without 'kubectl' prefix).
    Example: "get pods -n default" will run "kubectl get pods -n default"
    """
    # Build the full command
    command_parts = ["kubectl"] + request.command.split()
    full_command = " ".join(command_parts)

    start_time = time.time()

    try:
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            timeout=request.timeout
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        return KubectlResponse(
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            command=full_command,
            execution_time_ms=execution_time_ms
        )

    except subprocess.TimeoutExpired:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return KubectlResponse(
            stdout="",
            stderr=f"Command timed out after {request.timeout} seconds",
            return_code=-1,
            command=full_command,
            execution_time_ms=execution_time_ms
        )
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        raise HTTPException(
            status_code=500,
            detail=f"Error executing command: {str(e)}"
        )


@app.post("/run", response_model=KubectlResponse)
async def run_command(request: CommandRequest):
    """
    Execute a kubectl or helm command.

    The command should include the tool prefix (kubectl or helm).
    Examples:
    - "kubectl get pods -n default"
    - "helm list -A"
    - "helm install prometheus prometheus-community/kube-prometheus-stack"
    """
    command_parts = request.command.split()

    if not command_parts:
        raise HTTPException(status_code=400, detail="Empty command")

    # Validate command prefix for security
    tool = command_parts[0]
    if tool not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid command. Only {ALLOWED_COMMANDS} commands are allowed."
        )

    start_time = time.time()

    try:
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            timeout=request.timeout
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        return KubectlResponse(
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            command=request.command,
            execution_time_ms=execution_time_ms
        )

    except subprocess.TimeoutExpired:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return KubectlResponse(
            stdout="",
            stderr=f"Command timed out after {request.timeout} seconds",
            return_code=-1,
            command=request.command,
            execution_time_ms=execution_time_ms
        )
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        raise HTTPException(
            status_code=500,
            detail=f"Error executing command: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "kubectl-service",
        "description": "Execute kubectl and helm commands",
        "endpoints": {
            "/health": "Health check",
            "/execute": "Execute kubectl command (POST) - legacy",
            "/run": "Execute kubectl or helm command (POST)"
        }
    }
