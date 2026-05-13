"""ML model predictor - loads model once and caches in memory."""
import logging
from typing import Optional

import joblib

from .config import ML_MODEL_PATH

logger = logging.getLogger(__name__)

_model = None
_model_loaded = False


def _load_model():
    """Load the fraud detection model (singleton pattern)."""
    global _model, _model_loaded
    
    if _model_loaded:
        return _model
    
    try:
        logger.info(f"Loading fraud detection model from {ML_MODEL_PATH}")
        _model = joblib.load(ML_MODEL_PATH)
        _model_loaded = True
        logger.info("Fraud detection model loaded successfully")
        return _model
    except Exception as e:
        logger.error(f"Failed to load fraud detection model: {e}", exc_info=True)
        _model_loaded = True
        _model = None
        return None


def predict_transaction_fraud(features: dict) -> Optional[float]:
    """
    Predict fraud probability for a transaction.
    
    Args:
        features: Dictionary with keys matching training features:
            - amount
            - user_avg_amount
            - amount_ratio
            - tx_count_last_1h
            - tx_count_last_24h
            - is_new_device
            - is_trusted_device
            - is_new_ip
            - is_new_country
            - failed_logins_last_30m
            - hour_of_day
    
    Returns:
        Fraud probability (0.0 to 1.0) or None if prediction fails
    """
    model = _load_model()
    
    if model is None:
        logger.warning("Model not loaded, cannot make prediction")
        return None
    
    try:
        # Feature order must match training data
        feature_order = [
            'amount',
            'user_avg_amount',
            'amount_ratio',
            'tx_count_last_1h',
            'tx_count_last_24h',
            'is_new_device',
            'is_trusted_device',
            'is_new_ip',
            'is_new_country',
            'failed_logins_last_30m',
            'hour_of_day',
        ]
        
        # Build feature array in correct order
        feature_values = [features.get(f, 0) for f in feature_order]
        
        # Predict probability
        probability = model.predict_proba([feature_values])[0][1]
        
        return float(probability)
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        return None
