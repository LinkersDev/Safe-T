#!/usr/bin/env python3
"""
Train Random Forest fraud detection model.

Simple MVP training script - no hyperparameter tuning, just train and evaluate.
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def main():
    data_dir = Path(__file__).parent / "data"
    
    print("Loading training data...")
    train_df = pd.read_csv(data_dir / "train.csv")
    test_df = pd.read_csv(data_dir / "test.csv")
    
    # Separate features and labels
    X_train = train_df.drop(columns=["label"])
    y_train = train_df["label"]
    X_test = test_df.drop(columns=["label"])
    y_test = test_df["label"]
    
    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Features: {list(X_train.columns)}")
    print(f"Label distribution (train): {y_train.value_counts().to_dict()}")
    
    # Train Random Forest with class balancing
    print("\nTraining Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        max_depth=10,
        min_samples_split=10,
        min_samples_leaf=5
    )
    
    model.fit(X_train, y_train)
    print("Training complete!")
    
    # Evaluate on test set
    print("\nEvaluating on test set...")
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    
    print(f"\n{'='*50}")
    print("MODEL PERFORMANCE METRICS")
    print(f"{'='*50}")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"{'='*50}\n")
    
    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Normal", "Fraud"]))
    
    # Feature importance
    print("\nFeature Importance:")
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.iterrows():
        print(f"  {row['feature']:25s} {row['importance']:.4f}")
    
    # Save model
    model_path = Path(__file__).parent / "fraud_model.pkl"
    print(f"\nSaving model to {model_path}...")
    joblib.dump(model, model_path)
    print("Model saved successfully!")
    
    print(f"\n{'='*50}")
    print("TRAINING COMPLETE")
    print(f"{'='*50}")
    print(f"Model file: {model_path}")
    print(f"Ready for integration into Django backend")


if __name__ == "__main__":
    main()
