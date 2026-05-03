"""String choices and scoring thresholds for the risk engine."""
from decimal import Decimal


# ---------------------------------------------------------------------------
# Alert / Decision enumerations
# ---------------------------------------------------------------------------

class AlertType:
    TRANSACTION = "TRANSACTION"
    LOGIN       = "LOGIN"

    CHOICES = [
        (TRANSACTION, "Transaction"),
        (LOGIN,       "Login"),
    ]


class AlertSeverity:
    LOW      = "LOW"       # score  0-24 — no alert created
    MEDIUM   = "MEDIUM"    # score 25-49 — alert created
    HIGH     = "HIGH"      # score 50-74 — alert created
    CRITICAL = "CRITICAL"  # score 75+   — alert + auto-freeze (transactions)

    CHOICES = [
        (LOW,      "Low"),
        (MEDIUM,   "Medium"),
        (HIGH,     "High"),
        (CRITICAL, "Critical"),
    ]

    ORDERED = [LOW, MEDIUM, HIGH, CRITICAL]  # ascending severity

    @classmethod
    def for_score(cls, score: int) -> str:
        if score >= 75:
            return cls.CRITICAL
        if score >= 50:
            return cls.HIGH
        if score >= 25:
            return cls.MEDIUM
        return cls.LOW


class AlertStatus:
    OPEN      = "OPEN"       # awaiting Risk Officer review
    REVIEWED  = "REVIEWED"   # reviewed; decision recorded
    DISMISSED = "DISMISSED"  # officer decided no action
    ACTIONED  = "ACTIONED"   # officer applied an action (or auto-actioned)

    CHOICES = [
        (OPEN,      "Open"),
        (REVIEWED,  "Reviewed"),
        (DISMISSED, "Dismissed"),
        (ACTIONED,  "Actioned"),
    ]


class DecisionAction:
    DISMISS        = "DISMISS"
    WARN           = "WARN"
    FREEZE_ACCOUNT = "FREEZE_ACCOUNT"
    BLOCK_ACCOUNT  = "BLOCK_ACCOUNT"
    ESCALATE       = "ESCALATE"

    CHOICES = [
        (DISMISS,        "Dismiss — no action required"),
        (WARN,           "Warn — monitor, no account action"),
        (FREEZE_ACCOUNT, "Freeze Account"),
        (BLOCK_ACCOUNT,  "Block Account"),
        (ESCALATE,       "Escalate to senior officer"),
    ]


# ---------------------------------------------------------------------------
# Scoring rule parameters
# ---------------------------------------------------------------------------

class ScoringConfig:
    # Transaction amount rules
    AMOUNT_CRITICAL_THRESHOLD = Decimal("10000")  # USD → +75 pts (CRITICAL by itself)
    AMOUNT_CRITICAL_SCORE     = 75

    AMOUNT_HIGH_THRESHOLD     = Decimal("5000")   # USD → +40 pts
    AMOUNT_HIGH_SCORE         = 40

    # Velocity rules (debits in a rolling window)
    VELOCITY_WINDOW_HOURS = 1
    VELOCITY_COUNT_HIGH   = 5    # >= 5 debits/hr → +25
    VELOCITY_SCORE_HIGH   = 25
    VELOCITY_COUNT_MEDIUM = 3    # >= 3 debits/hr → +15
    VELOCITY_SCORE_MEDIUM = 15

    # Abnormal transaction hour (midnight–04:59 local/UTC)
    ABNORMAL_HOUR_START    = 0
    ABNORMAL_HOUR_END      = 4   # inclusive
    ABNORMAL_HOUR_TX_SCORE = 15

    # Login-specific rules
    ABNORMAL_HOUR_LOGIN_SCORE = 10
    NEW_DEVICE_SCORE          = 25
    NEW_COUNTRY_SCORE         = 20
    FAILED_LOGIN_HIGH_COUNT   = 3   # >= 3 failures in 30 min → +30
    FAILED_LOGIN_HIGH_SCORE   = 30
    FAILED_LOGIN_LOW_COUNT    = 1   # >= 1 failure in 30 min → +10
    FAILED_LOGIN_LOW_SCORE    = 10
    FAILED_LOGIN_WINDOW_MIN   = 30
