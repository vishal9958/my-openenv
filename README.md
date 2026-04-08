# ServerMaintenanceEnv - OpenEnv Hackathon Project

A simulated Unix system environment designed for training LLMs on server maintenance tasks.

## Environment Description
The `MyEnvV4Env` simulates a simple Unix server. The agent aims to restore service functionality for a degraded web service through reading logs, fixing files, and starting systemd properties.

## Action Space
Typed Pydantic action: `MyEnvV4Action`
Allows two types of actions:
- `action_type: "run_command"`: Run a shell command in the environment (e.g., `systemctl restart web`, `cat /var/log/syslog`). Allowed bash commands: `ls`, `cat`, `echo`, `systemctl`.
- `action_type: "submit"`: Declares task completion.

## Observation Space
The step result contains observations dictionary representing the server footprint:
- `last_output` (String): Standard output strings returned from the previous action execution.
- `service_status` (Dictionary): Provides the live state mappings for services on the system, containing attributes (`active`, `inactive`, `failed`).

## Setup Instructions

1. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run inference script manually:**
   The required execution sequence for evaluations outputs cleanly to terminal:
   ```bash
   export HF_TOKEN="your_token"
   export MODEL_NAME="your_model"
   python inference.py
   ```

3. **Deploy (Hugging Face Spaces):**
   The Dockerfile initializes `python -m openenv.cli serve --port 7860 --host 0.0.0.0 .` to launch the instance server, complying with Spaces architecture and port binding `7860`.

## Tasks Included
- **easy-restart:** (Easy) Detect downed state and use `systemctl start web`
- **medium-logfix:** (Medium) Read syslog, parse error about file `/etc/web/env.cfg` missing, create the configuration via `echo`, and restart.
- **hard-patch:** (Hard) Trace syslogs identifying syntax error on line 1, rewrite `/etc/web/config.txt` to fix `PORT=80` environment string, and successfully start web service.
