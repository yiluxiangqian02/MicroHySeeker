import asyncio
import os
import shutil
import time
from typing import Dict, Optional
from uuid import uuid4

from openviking.server.models import AgentTask, AgentTaskStatus, AgentType, CreateAgentTaskRequest
from openviking_cli.utils import get_logger

logger = get_logger(__name__)

class AgentTaskManager:
    """Manages the lifecycle of agent tasks."""

    def __init__(self, base_workdir: str, repo_root: str, agent_scripts_dir: str):
        self.base_workdir = base_workdir
        self.repo_root = repo_root
        self.agent_scripts_dir = agent_scripts_dir # Directory containing agent scripts
        self.tasks: Dict[str, AgentTask] = {}
        # TODO: Persist tasks to disk (e.g., JSON file) for recovery
        logger.info(
            f"AgentTaskManager initialized with base_workdir: {base_workdir}, "
            f"repo_root: {repo_root}, agent_scripts_dir: {agent_scripts_dir}"
        )

    async def create_task(self, request: CreateAgentTaskRequest) -> AgentTask:
        """Creates and starts a new agent task."""
        task_id = str(uuid4())
        created_at = time.time()
        
        task = AgentTask(
            id=task_id,
            description=request.description,
            agent_type=request.agent_type,
            status=AgentTaskStatus.PENDING,
            created_at=created_at,
        )
        self.tasks[task_id] = task

        # Start the task in a background coroutine
        asyncio.create_task(self._run_agent_task(task, request.context))
        logger.info(f"Agent task {task_id} created and started in background.")
        
        return task

    async def _run_agent_task(self, task: AgentTask, context: Optional[Dict]):
        """Internal method to execute the agent task."""
        try:
            # 1. Prepare worktree
            task.worktree_path = await self._prepare_worktree(task.id)
            task.status = AgentTaskStatus.RUNNING
            task.started_at = time.time()
            logger.info(f"Task {task.id}: Worktree prepared at {task.worktree_path}")

            # 2. Start agent script in the worktree
            agent_script_path = os.path.join(self.agent_scripts_dir, "run_agent.py")
            if not os.path.exists(agent_script_path):
                raise FileNotFoundError(f"Agent script not found: {agent_script_path}")
            
            # Construct command to run the Python agent script
            command = (
                f"python {agent_script_path} "
                f"--task_id {task.id} "
                f"--worktree_path {task.worktree_path} "
                f"--description \"{task.description}\" "
                f"--agent_type {task.agent_type.value}"
            )
            logger.info(f"Task {task.id}: Running agent command: {command}")
            
            await self._run_command(command, cwd=task.worktree_path) # Run the agent script
            
            task.status = AgentTaskStatus.SUCCESS
            task.completed_at = time.time()
            logger.info(f"Task {task.id} completed successfully.")

        except Exception as e:
            task.status = AgentTaskStatus.FAILED
            task.completed_at = time.time()
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)
        finally:
            if task.worktree_path:
                await self._cleanup_worktree(task) # Call cleanup here

    async def _prepare_worktree(self, task_id: str) -> str:
        """Prepares a git worktree for the agent task."""
        worktree_path = os.path.join(self.base_workdir, task_id)
        branch_name = f"agent-task-{task_id}"

        # Clean up existing worktree or branch if they exist
        if os.path.exists(worktree_path):
            logger.warning(f"Worktree path {worktree_path} already exists. Removing it.")
            shutil.rmtree(worktree_path)
        
        # Remove potentially existing local branch for a clean start
        await self._run_command(f"git -C {self.repo_root} branch -D {branch_name}", check_returncode=False)
        
        # Create a new worktree
        await self._run_command(
            f"git -C {self.repo_root} worktree add {worktree_path} -b {branch_name} origin/main",
            check_returncode=True
        )
        logger.info(f"Created git worktree: {worktree_path} on branch {branch_name}")
        return worktree_path

    async def _cleanup_worktree(self, task: AgentTask):
        """Cleans up the git worktree and associated branch."""
        if task.worktree_path and os.path.exists(task.worktree_path):
            logger.info(f"Cleaning up worktree at {task.worktree_path}")
            shutil.rmtree(task.worktree_path)
            # Remove worktree entry
            await self._run_command(
                f"git -C {self.repo_root} worktree prune",
                check_returncode=True
            )
            # Remove branch
            if task.id:
                branch_name = f"agent-task-{task.id}"
                await self._run_command(
                    f"git -C {self.repo_root} branch -D {branch_name}",
                    check_returncode=False # Allow failure if branch is already gone
                )
            logger.info(f"Worktree and branch for task {task.id} cleaned up.")

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Retrieves an agent task by ID."""
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancels an ongoing agent task."""
        task = self.tasks.get(task_id)
        if task and task.status == AgentTaskStatus.RUNNING:
            # TODO: Implement actual process termination (e.g., kill tmux session)
            task.status = AgentTaskStatus.CANCELLED
            task.completed_at = time.time()
            logger.info(f"Task {task_id} cancelled.")
            return True
        return False
    
    async def _run_command(self, command: str, cwd: Optional[str] = None, check_returncode: bool = True):
        """Helper to run shell commands."""
        logger.debug(f"Running command: {command} in cwd: {cwd}")
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if check_returncode and proc.returncode != 0:
            raise RuntimeError(f"Command '{command}' failed with error:\n{stderr.decode()}")
        return stdout.decode()
