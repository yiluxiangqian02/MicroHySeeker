from fastapi import APIRouter, Depends, HTTPException, status
from openviking.server.dependencies import get_service
from openviking.server.models import CreateAgentTaskRequest, AgentTask, AgentTaskStatus # Import new models
from openviking.service.core import OpenVikingService

router = APIRouter(prefix="/agent-tasks", tags=["Agent Tasks"])

@router.post("/", response_model=AgentTask)
async def create_agent_task(
    request: CreateAgentTaskRequest, # Use the new request model
    service: OpenVikingService = Depends(get_service)
):
    """
    Create a new agent task.
    """
    task = await service.agent_tasks.create_task(request)
    return task

@router.get("/{task_id}", response_model=AgentTask)
async def get_agent_task_status(
    task_id: str,
    service: OpenVikingService = Depends(get_service)
):
    """
    Get the status of an agent task.
    """
    task = service.agent_tasks.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent task not found")
    return task

@router.post("/{task_id}/cancel", response_model=AgentTask)
async def cancel_agent_task(
    task_id: str,
    service: OpenVikingService = Depends(get_service)
):
    """
    Cancel an ongoing agent task.
    """
    success = await service.agent_tasks.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not cancel task or task not running")
    task = service.agent_tasks.get_task(task_id) # Get updated task status
    return task
