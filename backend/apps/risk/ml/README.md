# ML Fraud Detection Module

This module provides ML-based fraud detection for transactions using a Random Forest classifier.

## Quick Start

The ML model is automatically loaded when Django starts. No manual initialization required.

## How It Works

1. **Transaction occurs** → `post_transaction()` creates transaction
2. **On commit** → `score_transaction()` is called
3. **Feature extraction** → `extract_transaction_features()` builds 10 features
4. **ML prediction** → `predict_transaction_fraud()` returns probability (0-1)
5. **Hybrid scoring** → Combines ML (60%) + rules (40%)
6. **Alert creation** → If score >= MEDIUM threshold
7. **Auto-freeze** → If CRITICAL AND rule_score >= 50

## Features (10 total)

1. **amount** - Transaction amount
2. **user_avg_amount** - User's historical average
3. **amount_ratio** - amount / user_avg_amount
4. **tx_count_last_1h** - Velocity (1 hour)
5. **tx_count_last_24h** - Velocity (24 hours)
6. **is_new_device** - Device not seen before
7. **is_trusted_device** - Device marked as trusted
8. **is_new_ip** - IP not seen before
9. **is_new_country** - Country not seen before
10. **failed_logins_last_30m** - Recent failed logins
11. **hour_of_day** - Hour of transaction (0-23)

## Telemetry Requirements

For ML to work properly, transactions must include telemetry in `metadata_json`:

```python
Transaction.objects.create(
    # ... other fields ...
    metadata_json={
        "ip_address": "192.168.1.1",
        "device_id": "device-uuid-here",
        "user_agent": "Mozilla/5.0 ...",
        "geo_country": "US",
    }
)
```

## Configuration

Edit `config.py` to adjust weights:

```python
ML_WEIGHT = 0.6      # ML contribution to final score
RULE_WEIGHT = 0.4    # Rule contribution to final score
```

## Scoring Formula

```python
combined_score = (rule_score * 0.4) + (ml_probability * 100 * 0.6)
```

## Auto-Freeze Logic

Account is auto-frozen if **BOTH** conditions are met:
- `combined_score >= 75` (CRITICAL threshold)
- `rule_score >= 50` (rule engine confirmation)

This ensures rule engine has final authority.

## Graceful Degradation

If ML fails for any reason:
- System falls back to rule-based scoring only
- Transaction processing continues normally
- Error is logged but not surfaced to user

## Model Performance

- **Recall:** 93.86% (catches most fraud)
- **Precision:** 60.79% (acceptable false positives)
- **ROC-AUC:** 96.55% (excellent discrimination)

## Retraining the Model

1. Collect new labeled data from production
2. Update `ml/data/train.csv` and `ml/data/test.csv`
3. Run training script:
   ```bash
   cd ml
   python train_model.py
   ```
4. Copy new model to backend:
   ```bash
   copy fraud_model.pkl ..\backend\apps\risk\ml\fraud_model.pkl
   ```
5. Restart Django server

## Troubleshooting

### Model not loading
- Check that `fraud_model.pkl` exists in this directory
- Check Django logs for "Loading fraud detection model" message
- Verify scikit-learn version matches training version

### Features not extracting
- Ensure transaction has `metadata_json` with telemetry
- Check that user has transaction history for avg calculation
- Verify LoginLog and UserDevice tables are populated

### Predictions always None
- Check Django logs for ML prediction errors
- Verify model file is not corrupted
- Ensure all 10 features are present in feature dict

## Testing

Run integration tests:
```bash
python manage.py test apps.risk.tests.test_ml_integration --settings=config.settings.test
```

## Monitoring

Check logs for:
- `"Fraud scoring | tx=..."` - Shows all three scores
- `"Account auto-frozen | tx=..."` - Freeze decisions
- `"ML prediction failed for tx..."` - ML errors

## API Response

FraudAlert objects now include:
```json
{
  "id": 123,
  "ml_fraud_probability": 0.85,
  "rule_based_score": 60,
  "combined_score": 75,
  "severity": "CRITICAL",
  "rules_triggered": ["High velocity: 10 debits in last 1h"],
  ...
}
```

## No Automatic Retraining

This system does NOT automatically retrain. Model updates are manual only.
Risk Officer decisions are logged but NOT used for auto-retraining.
