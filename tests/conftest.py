import sys
from unittest.mock import MagicMock

sys.modules.setdefault("opentelemetry", MagicMock())
sys.modules.setdefault("opentelemetry.trace", MagicMock())
