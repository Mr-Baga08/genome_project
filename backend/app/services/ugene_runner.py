# backend/app/services/ugene_runner.py
import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, NamedTuple
from ..models.task import Task

class ExecutionResult(NamedTuple):
    success: bool
    stdout: str
    stderr: str
    output_files: List[str]
    return_code: int

class UgeneRunner:
    def __init__(self, ugene_image: str = "ugene_sdk_docker_image"):
        self.ugene_image = ugene_image
        self.work_dir = Path("/tmp/ugene_workdir")
        self.work_dir.mkdir(exist_ok=True)

    async def execute_task(self, task: Task) -> ExecutionResult:
        """Execute UGENE task in Docker container"""
        # Create unique workspace for this task
        task_workspace = self.work_dir / task.task_id
        task_workspace.mkdir(exist_ok=True)
        
        try:
            # Prepare input files
            await self._prepare_input_files(task, task_workspace)
            
            # Build Docker command
            docker_cmd = self._build_docker_command(task, task_workspace)
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=task_workspace
            )
            
            stdout, stderr = await process.communicate()
            
            # Collect output files
            output_files = self._collect_output_files(task_workspace)
            
            return ExecutionResult(
                success=process.returncode == 0,
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8'), 
                output_files=output_files,
                return_code=process.returncode
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution failed: {str(e)}",
                output_files=[],
                return_code=-1
            )
        finally:
            # Cleanup workspace
            # shutil.rmtree(task_workspace, ignore_errors=True)
            pass

    def _build_docker_command(self, task: Task, workspace: Path) -> List[str]:
        """Build Docker command for UGENE execution"""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{workspace}:/data",
            "-w", "/data",
            self.ugene_image
        ]
        
        # Add UGENE commands
        for ugene_cmd in task.commands:
            cmd.extend(ugene_cmd.split())
            
        return cmd

    async def _prepare_input_files(self, task: Task, workspace: Path):
        """Copy input files to task workspace"""
        for input_file in task.input_files:
            if os.path.exists(input_file):
                dest_file = workspace / os.path.basename(input_file)
                shutil.copy2(input_file, dest_file)

    def _collect_output_files(self, workspace: Path) -> List[str]:
        """Collect generated output files"""
        output_files = []
        for file_path in workspace.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                # Copy to permanent storage and return URL
                # Implementation depends on your file storage strategy
                output_files.append(str(file_path))
        return output_files
