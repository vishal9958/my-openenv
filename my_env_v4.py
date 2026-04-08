from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal, List
from openenv.core.client_types import StepResult

class MyEnvV4Action(BaseModel):
    """The allowed actions for the ServerMaintenance agent."""
    action_type: Literal["run_command", "submit"] = Field(
        ..., description="The type of action to perform. 'run_command' executes a shell command on the simulated server, 'submit' ends the task."
    )
    command: Optional[str] = Field(
        None, description="The command to execute, if action_type is 'run_command'. e.g. 'cat /var/log/syslog', 'systemctl restart web', 'echo \"fix\" > config.txt'."
    )

class MyEnvV4State(BaseModel):
    task_name: str
    filesystem: Dict[str, str]
    service_status: Dict[str, str]
    last_output: str
    steps_taken: int
    done: bool
    reward: float

class MyEnvV4Env:
    """
    A simulated Server Maintenance environment.
    Tasks:
    - easy-restart: A web service is down. Restart it. ('systemctl restart web')
    - medium-logfix: A web service is down due to a missing file. Check logs, create file, restart.
    - hard-patch: A web service is down due to a syntax error in config.txt. Fix syntax, restart.
    """
    
    def __init__(self, **kwargs):
        self.state = None
    
    def _init_easy(self):
        return {
            "filesystem": {"/var/log/syslog": "web service stopped."},
            "service_status": {"web": "inactive"},
        }
    
    def _init_medium(self):
        return {
            "filesystem": {"/var/log/syslog": "FATAL: /etc/web/env.cfg missing. Cannot start web service."},
            "service_status": {"web": "failed"},
        }
    
    def _init_hard(self):
        return {
            "filesystem": {
                "/var/log/syslog": "FATAL: Syntax error in /etc/web/config.txt on line 1: expected value",
                "/etc/web/config.txt": "PORT=\nHOST=localhost"
            },
            "service_status": {"web": "failed"},
        }
    
    def reset(self, task: str = "easy-restart") -> Dict[str, Any]:
        """Resets the environment for a given task."""
        if task == "easy-restart":
            init_data = self._init_easy()
        elif task == "medium-logfix":
            init_data = self._init_medium()
        elif task == "hard-patch":
            init_data = self._init_hard()
        else:
            task = "easy-restart"
            init_data = self._init_easy()

        self.state = MyEnvV4State(
            task_name=task,
            filesystem=init_data["filesystem"],
            service_status=init_data["service_status"],
            last_output="System booted. Waiting for commands. (Available: ls, cat, echo, systemctl)",
            steps_taken=0,
            done=False,
            reward=0.0
        )
        return self._observation()

    def state(self) -> Dict[str, Any]:
        return self.state.model_dump() if self.state else {}

    def _observation(self) -> Dict[str, Any]:
        return {
            "last_output": self.state.last_output,
            "service_status": self.state.service_status
        }
        
    def _grade(self) -> float:
        """Grading logic (easy, medium, hard). Returns a score between 0.0 and 1.0."""
        score = 0.0
        if self.state.task_name == "easy-restart":
            if self.state.service_status.get("web") == "active":
                score = 1.0
        elif self.state.task_name == "medium-logfix":
            if "/etc/web/env.cfg" in self.state.filesystem:
                score += 0.5
            if self.state.service_status.get("web") == "active":
                score += 0.5
        elif self.state.task_name == "hard-patch":
            content = self.state.filesystem.get("/etc/web/config.txt", "")
            if "PORT=80" in content or "PORT=8080" in content:  # Accept any valid looking port assignment
                score += 0.5
            elif "PORT=" not in content or len((content.split("PORT=")[1] or " ").split()[0]) > 0:
                score += 0.5
            if self.state.service_status.get("web") == "active":
                score += 0.5
        return min(score, 1.0)

    def _handle_systemctl(self, args: List[str]) -> str:
        if len(args) < 3:
            return "Usage: systemctl <cmd> <service>"
        cmd = args[1]
        svc = args[2]
        
        if svc not in self.state.service_status:
            return f"Unit {svc}.service could not be found."
            
        if cmd == "status":
            return f"Service {svc} is {self.state.service_status[svc]}."
        elif cmd == "restart" or cmd == "start":
            # Simulate checking specific constraints
            if self.state.task_name == "easy-restart":
                self.state.service_status[svc] = "active"
                return f"Started {svc}."
            elif self.state.task_name == "medium-logfix":
                if "/etc/web/env.cfg" in self.state.filesystem:
                    self.state.service_status[svc] = "active"
                    return f"Started {svc}."
                else:
                    return "Job for web.service failed. See 'syslog' for details."
            elif self.state.task_name == "hard-patch":
                content = self.state.filesystem.get("/etc/web/config.txt", "")
                # Simplistic syntax check: PORT is assigned a value
                if "PORT=" in content and len((content.split("PORT=")[1] or " ").split()) > 0 and (content.split("PORT=")[1] or " ").split()[0] != "":
                    self.state.service_status[svc] = "active"
                    return f"Started {svc}."
                else:
                    return "Job for web.service failed. See 'syslog' for details."
        elif cmd == "stop":
            self.state.service_status[svc] = "inactive"
            return f"Stopped {svc}."
        return f"Unknown systemctl command {cmd}"

    def _handle_command(self, cmd_line: str) -> str:
        parts = cmd_line.strip().split()
        if not parts:
            return ""
            
        prog = parts[0]
        
        if prog == "ls":
            return " ".join(self.state.filesystem.keys())
        elif prog == "cat":
            if len(parts) > 1:
                return self.state.filesystem.get(parts[1], f"cat: {parts[1]}: No such file or directory")
            return "cat: missing operand"
        elif prog == "echo":
            # simplistic parsing for `echo "content" > file`
            import shlex
            try:
                tokens = shlex.split(cmd_line)
            except Exception:
                tokens = parts
                
            if len(tokens) >= 4 and ">" in tokens:
                idx = tokens.index(">")
                content = " ".join(tokens[1:idx])
                file_path = tokens[idx+1]
                self.state.filesystem[file_path] = content
                return ""
            elif len(tokens) >= 4 and ">>" in tokens:
                idx = tokens.index(">>")
                content = " ".join(tokens[1:idx])
                file_path = tokens[idx+1]
                existing = self.state.filesystem.get(file_path, "")
                self.state.filesystem[file_path] = existing + "\n" + content
                return ""
            else:
                return " ".join(tokens[1:])
        elif prog == "systemctl":
            return self.handle_systemctl(parts) # Wait, should be _handle_systemctl
        else:
            return f"{prog}: command not found"

    def step(self, action: MyEnvV4Action) -> StepResult:
        if self.state.done:
            return StepResult(observation=self._observation(), reward=0.0, done=True)
            
        self.state.steps_taken += 1
        
        # In case action is a dictionary (from GenericClient) or a Pydantic model
        if isinstance(action, dict):
            action_type = action.get("action_type")
            command = action.get("command")
        else:
            action_type = action.action_type
            command = action.command

        if action_type == "submit":
            self.state.done = True
            self.state.last_output = "Task submitted."
        elif action_type == "run_command" and command:
            if command.startswith("systemctl"):
                output = self._handle_systemctl(command.split())
            else:
                output = self._handle_command(command)
            self.state.last_output = output
        else:
            self.state.last_output = "Invalid action."
            
        # Compute partial or full reward
        curr_reward = self._grade()
        step_reward = curr_reward - self.state.reward
        self.state.reward = curr_reward
        
        # Auto-complete if full credit earned
        if self.state.reward >= 1.0:
            self.state.done = True
            
        return StepResult(
            observation=self._observation(),
            reward=round(step_reward, 2),
            done=self.state.done
        )
