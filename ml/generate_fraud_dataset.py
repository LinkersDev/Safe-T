#!/usr/bin/env python3
"""
Synthetic fintech-wallet transaction rows for fraud detection (Random Forest, etc.).

Cohort simulation: 70% normal, 20% suspicious (noisy labels), 10% fraud — not i.i.d. uniform noise.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

COLUMNS = [
    "amount",
    "user_avg_amount",
    "amount_ratio",
    "tx_count_last_1h",
    "tx_count_last_24h",
    "is_new_device",
    "is_trusted_device",
    "is_new_ip",
    "is_new_country",
    "failed_logins_last_30m",
    "label",
]


def _lognormal_positive(rng: np.random.Generator, n: int, mean: float, sigma: float) -> np.ndarray:
    """Log-normal draws with approximate target mean; clipped away from zero."""
    mu = float(np.log(mean) - 0.5 * sigma**2)
    return rng.lognormal(mu, sigma, size=n).clip(min=1.0, max=500_000.0)


def _cohort_counts(n_rows: int) -> tuple[int, int, int]:
    n_normal = int(round(n_rows * 0.70))
    n_suspicious = int(round(n_rows * 0.20))
    n_fraud = n_rows - n_normal - n_suspicious
    if n_fraud < 0:
        raise ValueError("n_rows too small for 70/20/10 split")
    return n_normal, n_suspicious, n_fraud


def generate_rows(n_rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_normal, n_suspicious, n_fraud = _cohort_counts(n_rows)
    parts: list[pd.DataFrame] = []

    # --- Normal (label 0) ---
    n = n_normal
    user_avg = _lognormal_positive(rng, n, mean=88.0, sigma=0.52)
    ratio = rng.uniform(0.5, 1.5, size=n) * rng.lognormal(0.0, 0.035, size=n)
    ratio = np.clip(ratio, 0.48, 1.58)
    amount = user_avg * ratio

    tx1 = rng.poisson(0.85, size=n)
    tx_extra = rng.poisson(2.4, size=n)
    tx24 = np.maximum(tx1 + tx_extra, tx1)

    new_dev = rng.binomial(1, 0.055, size=n)
    new_ip = rng.binomial(1, 0.065, size=n)
    new_country = rng.binomial(1, 0.011, size=n)
    trusted = np.where(
        (new_dev + new_ip) > 0,
        rng.binomial(1, 0.12, size=n),
        rng.binomial(1, 0.935, size=n),
    )
    failed = rng.poisson(0.11, size=n)

    df_n = pd.DataFrame(
        {
            "amount": amount,
            "user_avg_amount": user_avg,
            "tx_count_last_1h": tx1,
            "tx_count_last_24h": tx24,
            "is_new_device": new_dev,
            "is_trusted_device": trusted,
            "is_new_ip": new_ip,
            "is_new_country": new_country,
            "failed_logins_last_30m": failed,
            "label": np.zeros(n, dtype=np.int8),
        }
    )
    parts.append(df_n)

    # --- Suspicious (noisy labels via latent risk) ---
    n = n_suspicious
    user_avg = _lognormal_positive(rng, n, mean=96.0, sigma=0.62)
    elevated = rng.random(size=n) < 0.78
    ratio_elev = rng.uniform(1.5, 3.0, size=n)
    ratio_overlap = rng.uniform(0.72, 1.48, size=n)
    ratio = np.where(elevated, ratio_elev, ratio_overlap) * rng.lognormal(0.0, 0.055, size=n)
    ratio = np.clip(ratio, 0.52, 3.15)
    amount = user_avg * ratio

    tx1 = rng.poisson(2.9, size=n)
    tx_extra = rng.poisson(6.2, size=n)
    tx24 = np.maximum(tx1 + tx_extra, tx1)

    new_dev = rng.binomial(1, 0.29, size=n)
    new_ip = rng.binomial(1, 0.33, size=n)
    new_country = rng.binomial(1, 0.085, size=n)
    trusted = np.where(new_dev > 0, rng.binomial(1, 0.11, size=n), rng.binomial(1, 0.58, size=n))
    failed = rng.poisson(1.05, size=n)

    z = (
        1.15 * (ratio - 1.45)
        + 0.14 * tx1
        + 0.88 * new_dev
        + 0.82 * new_ip
        + 1.05 * new_country
        + 0.24 * np.minimum(failed, 8)
        - 0.38 * trusted
    )
    p_fraud = 1.0 / (1.0 + np.exp(-(z - 0.32)))
    p_fraud = np.clip(p_fraud, 0.07, 0.40)
    label_s = rng.binomial(1, p_fraud, size=n).astype(np.int8)

    df_s = pd.DataFrame(
        {
            "amount": amount,
            "user_avg_amount": user_avg,
            "tx_count_last_1h": tx1,
            "tx_count_last_24h": tx24,
            "is_new_device": new_dev,
            "is_trusted_device": trusted,
            "is_new_ip": new_ip,
            "is_new_country": new_country,
            "failed_logins_last_30m": failed,
            "label": label_s,
        }
    )
    parts.append(df_s)

    # --- Fraud (label 1) ---
    n = n_fraud
    user_avg = _lognormal_positive(rng, n, mean=78.0, sigma=0.58)
    ratio = rng.uniform(3.0, 10.0, size=n) * rng.lognormal(0.015, 0.048, size=n)
    ratio = np.clip(ratio, 3.0, 11.5)
    amount = user_avg * ratio

    tx1 = rng.poisson(11.5, size=n)
    tx_extra = rng.poisson(18.0, size=n)
    tx24 = np.maximum(tx1 + tx_extra, tx1)

    new_dev = np.ones(n, dtype=np.int8)
    new_ip = np.ones(n, dtype=np.int8)
    new_country = rng.binomial(1, 0.76, size=n)
    trusted = np.zeros(n, dtype=np.int8)
    failed = rng.poisson(4.2, size=n)

    df_f = pd.DataFrame(
        {
            "amount": amount,
            "user_avg_amount": user_avg,
            "tx_count_last_1h": tx1,
            "tx_count_last_24h": tx24,
            "is_new_device": new_dev,
            "is_trusted_device": trusted,
            "is_new_ip": new_ip,
            "is_new_country": new_country,
            "failed_logins_last_30m": failed,
            "label": np.ones(n, dtype=np.int8),
        }
    )
    parts.append(df_f)

    df = pd.concat(parts, ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    df["amount"] = df["amount"].round(2)
    df["user_avg_amount"] = df["user_avg_amount"].round(2)
    df["user_avg_amount"] = df["user_avg_amount"].replace(0.0, 1.0)
    df["amount_ratio"] = (df["amount"] / df["user_avg_amount"]).astype(np.float64)

    for c in ("tx_count_last_1h", "tx_count_last_24h"):
        df[c] = df[c].clip(lower=0).astype(np.int64)
    df["failed_logins_last_30m"] = df["failed_logins_last_30m"].clip(lower=0, upper=15).astype(np.int64)
    for c in ("is_new_device", "is_trusted_device", "is_new_ip", "is_new_country", "label"):
        df[c] = df[c].astype(np.int8)

    # Enforce velocity constraint after integer cast
    bad = df["tx_count_last_24h"] < df["tx_count_last_1h"]
    if bad.any():
        df.loc[bad, "tx_count_last_24h"] = df.loc[bad, "tx_count_last_1h"]

    # Trusted device rarely 1 when brand-new device (production-like)
    both = (df["is_new_device"] == 1) & (df["is_trusted_device"] == 1)
    if both.any():
        df.loc[both, "is_trusted_device"] = 0

    df = df[COLUMNS]
    return df


def validate(df: pd.DataFrame, n_rows: int) -> None:
    assert len(df) == n_rows, f"expected {n_rows} rows, got {len(df)}"
    assert not df.isna().any().any(), "NaNs in dataset"
    assert set(df.columns) == set(COLUMNS)
    ratio_chk = (df["amount"] / df["user_avg_amount"]) - df["amount_ratio"]
    assert ratio_chk.abs().max() < 1e-6, "amount_ratio inconsistent with amount / user_avg_amount"
    assert df["label"].isin((0, 1)).all()
    assert (df[["is_new_device", "is_trusted_device", "is_new_ip", "is_new_country", "label"]].isin((0, 1))).all().all()
    assert (df["tx_count_last_24h"] >= df["tx_count_last_1h"]).all()
    pos = int(df["label"].sum())
    assert pos > 0, "need at least one positive label"
    assert pos < len(df), "need at least one negative label"


def main() -> None:
    p = argparse.ArgumentParser(description="Generate synthetic fraud dataset CSVs.")
    p.add_argument("--n-rows", type=int, default=20_000, help="Total rows (default 20000)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
        help="Output directory for CSV files",
    )
    p.add_argument("--test-size", type=float, default=0.2, help="Fraction for test split")
    args = p.parse_args()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    df = generate_rows(args.n_rows, args.seed)
    validate(df, args.n_rows)

    full_path = out_dir / "fraud_dataset.csv"
    df.to_csv(full_path, index=False)

    X = df.drop(columns=["label"])
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=y,
    )
    train_df = pd.concat([X_train, y_train], axis=1)[COLUMNS]
    test_df = pd.concat([X_test, y_test], axis=1)[COLUMNS]
    train_df.to_csv(out_dir / "train.csv", index=False)
    test_df.to_csv(out_dir / "test.csv", index=False)

    pos_rate = float(df["label"].mean())
    print(f"Wrote {full_path} ({len(df)} rows)")
    print(f"Wrote {out_dir / 'train.csv'} ({len(train_df)}), {out_dir / 'test.csv'} ({len(test_df)})")
    print(f"Label distribution: label=1 -> {int(df['label'].sum())} ({pos_rate:.2%}), label=0 -> {int((df['label'] == 0).sum())}")


if __name__ == "__main__":
    main()
