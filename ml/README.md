# Synthetic fraud dataset (wallet / fintech)

Offline data for training models such as **Random Forest** on tabular fraud signals.

## Generate CSVs

```bash
cd ml
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python generate_fraud_dataset.py
```

Outputs (default `--out-dir data/`):

- `data/fraud_dataset.csv` — full set (default 20,000 rows)
- `data/train.csv` / `data/test.csv` — stratified 80/20 split on `label`

Options:

```text
python generate_fraud_dataset.py --help
python generate_fraud_dataset.py --n-rows 20000 --seed 42 --out-dir data
```

## Evaluation tips

The label distribution is **imbalanced** (realistic). Prefer **PR-AUC** or use `class_weight='balanced'` in `RandomForestClassifier` rather than expecting high raw accuracy alone.

## Regenerating data

`data/*.csv` are reproducible for a fixed `--seed`. Re-run the script after changing cohort parameters in `generate_fraud_dataset.py`.
