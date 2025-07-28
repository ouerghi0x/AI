# env_loader.py
import os
from dotenv import load_dotenv

def load_environment():
    env_name = os.getenv("ENVIRONMENT", "dev")  # default to dev
    env_file = f".env.{env_name}"
    load_dotenv(dotenv_path=env_file)
