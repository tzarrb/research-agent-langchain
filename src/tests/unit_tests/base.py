import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Virtual environment: {os.environ.get('VIRTUAL_ENV', 'Not in venv')}")