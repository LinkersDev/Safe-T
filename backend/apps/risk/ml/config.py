"""ML module configuration."""
from pathlib import Path

ML_MODEL_PATH = Path(__file__).parent / "fraud_model.pkl"
ML_WEIGHT = 0.6
RULE_WEIGHT = 0.4
