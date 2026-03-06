import json
import os
import sys

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix, classification_report,
    roc_curve, roc_auc_score, precision_recall_curve
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    TRAINING_DATA_PATH, RF_MODEL_PATH, SCALER_PATH,
    TRAINING_OUTPUT_DIR
)


def load_model_and_data():
    """Load trained model, scaler, and test data"""
    print("Loading model and data...")

    # Load model
    if not os.path.exists(RF_MODEL_PATH):
        print(f"✗ Model not found at: {RF_MODEL_PATH}")
        print("Train the model first: python ml_training/train_model.py")
        return None, None, None, None, None

    model = joblib.load(RF_MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    # Load training data
    df = pd.read_csv(TRAINING_DATA_PATH)

    # Prepare test data (use last 15% as test)
    from sklearn.model_selection import train_test_split
    X = df.drop('conflict', axis=1)
    y = df['conflict']

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )

    # Scale
    X_test_scaled = scaler.transform(X_test)

    print(f"✓ Model loaded")
    print(f"✓ Test data loaded: {len(X_test)} samples")

    return model, scaler, X_test, X_test_scaled, y_test


def plot_confusion_matrix(y_true, y_pred, save_path):
    """Plot confusion matrix"""
    cm = confusion_matrix(y_true, y_pred)

    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['No Conflict', 'Conflict'],
                yticklabels=['No Conflict', 'Conflict'])
    plt.title('Confusion Matrix')
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Confusion matrix saved to: {save_path}")
    plt.close()


def plot_roc_curve(y_true, y_pred_proba, save_path):
    """Plot ROC curve"""
    fpr, tpr, _ = roc_curve(y_true, y_pred_proba)
    roc_auc = roc_auc_score(y_true, y_pred_proba)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2,
             label=f'ROC curve (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic (ROC) Curve')
    plt.legend(loc="lower right")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ ROC curve saved to: {save_path}")
    plt.close()


def plot_precision_recall_curve(y_true, y_pred_proba, save_path):
    """Plot precision-recall curve"""
    precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)

    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, color='blue', lw=2)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Precision-Recall curve saved to: {save_path}")
    plt.close()


def plot_feature_importance(model, feature_names, save_path, top_n=15):
    """Plot feature importance"""
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]

    plt.figure(figsize=(10, 6))
    plt.bar(range(top_n), importances[indices])
    plt.xticks(range(top_n), [feature_names[i] for i in indices], rotation=45, ha='right')
    plt.xlabel('Features')
    plt.ylabel('Importance')
    plt.title(f'Top {top_n} Feature Importances')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✓ Feature importance saved to: {save_path}")
    plt.close()


def generate_evaluation_report(model, X_test, X_test_scaled, y_test):
    """Generate comprehensive evaluation report"""
    print("\n" + "=" * 60)
    print("Model Evaluation Report")
    print("=" * 60 + "\n")

    # Predictions
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

    # Classification report
    print("Classification Report:")
    print(classification_report(y_test, y_pred,
                                target_names=['No Conflict', 'Conflict']))

    # Confusion matrix values
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    print("\nDetailed Metrics:")
    print(f"  True Negatives:  {tn}")
    print(f"  False Positives: {fp}")
    print(f"  False Negatives: {fn}")
    print(f"  True Positives:  {tp}")

    # Calculate additional metrics
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    print(f"\n  Sensitivity (Recall): {sensitivity:.4f}")
    print(f"  Specificity:          {specificity:.4f}")

    # ROC-AUC
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    print(f"  ROC-AUC:              {roc_auc:.4f}")

    # Generate plots
    print("\nGenerating visualizations...")

    output_dir = TRAINING_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    # Confusion matrix
    cm_path = os.path.join(output_dir, 'confusion_matrix.png')
    plot_confusion_matrix(y_test, y_pred, cm_path)

    # ROC curve
    roc_path = os.path.join(output_dir, 'roc_curve.png')
    plot_roc_curve(y_test, y_pred_proba, roc_path)

    # Precision-Recall curve
    pr_path = os.path.join(output_dir, 'precision_recall_curve.png')
    plot_precision_recall_curve(y_test, y_pred_proba, pr_path)

    # Feature importance
    feature_names = X_test.columns.tolist()
    fi_path = os.path.join(output_dir, 'feature_importance.png')
    plot_feature_importance(model, feature_names, fi_path)

    # Save detailed report
    report = {
        'confusion_matrix': {
            'tn': int(tn), 'fp': int(fp),
            'fn': int(fn), 'tp': int(tp)
        },
        'metrics': {
            'sensitivity': float(sensitivity),
            'specificity': float(specificity),
            'roc_auc': float(roc_auc)
        },
        'feature_importance': {
            feature_names[i]: float(importances)
            for i, importances in enumerate(model.feature_importances_)
        }
    }

    report_path = os.path.join(output_dir, 'evaluation_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"✓ Evaluation report saved to: {report_path}")

    print("\n" + "=" * 60)
    print("Evaluation Complete!")
    print("=" * 60)


def main():
    """Main evaluation function"""
    # Load model and data
    model, scaler, X_test, X_test_scaled, y_test = load_model_and_data()

    if model is None:
        return

    # Generate evaluation report
    generate_evaluation_report(model, X_test, X_test_scaled, y_test)


if __name__ == '__main__':
    main()