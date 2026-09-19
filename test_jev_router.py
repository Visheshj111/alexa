import sys
from pathlib import Path

# Add voice-agent-offline to sys.path
agent_dir = Path(__file__).resolve().parent / "voice-agent-offline"
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

from test_jev_router import test_router

if __name__ == "__main__":
    test_router()

