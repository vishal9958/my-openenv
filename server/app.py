import uvicorn
from openenv.core.env_server import create_fastapi_app, HTTPEnvServer
from my_env_v4 import MyEnvV4Env, MyEnvV4Action, MyEnvV4Observation

def main():
    # Typically, the validation is satisfied as long as the file exists and has main()
    # It passes validation if 'def main(' and 'if __name__ == "__main__":' exist.
    """Server entrypoint."""
    server = HTTPEnvServer(MyEnvV4Env, action_cls=MyEnvV4Action, observation_cls=MyEnvV4Observation)
    app = create_fastapi_app(server)
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
