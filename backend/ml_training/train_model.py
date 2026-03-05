import json
import os
import sys

import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, roc_auc_score, roc_curve
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    TRAINING_DATA_PATH, RF_MODEL_PATH, SCALER_PATH,
    METRICS_PATH, MODELS_DIR, RANDOM_STATE,
    TEST_SIZE, VALIDATION_SIZE, PLOTS_DIR
)

# Set style for plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)


def load_training_data():
    """Load training data"""
    print("Loading training data...")

    if not os.path.exists(TRAINING_DATA_PATH):
        print(f"✗ Training data not found at: {TRAINING_DATA_PATH}")
        print("Run: python ml_training/preprocessing/create_training_data.py")
        return None

    df = pd.read_csv(TRAINING_DATA_PATH)
    print(f"✓ Loaded {len(df)} samples")
    print(f"  Features: {len(df.columns) - 1}")
    print(f"  Positive: {df['conflict'].sum()}")
    print(f"  Negative: {len(df) - df['conflict'].sum()}")
    print(f"  Class balance: {df['conflict'].sum() / len(df) * 100:.1f}% positive")

    return df


def prepare_data(df):
    """Split data into train/validation/test sets"""
    print("\nPreparing data...")

    # Separate features and labels
    X = df.drop('conflict', axis=1)
    y = df['conflict']

    # First split: train+val and test
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    # Second split: train and validation
    val_ratio = VALIDATION_SIZE / (1 - TEST_SIZE)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_ratio, random_state=RANDOM_STATE, stratify=y_temp
    )

    print(f"✓ Train set: {len(X_train)} samples")
    print(f"  Validation set: {len(X_val)} samples")
    print(f"  Test set: {len(X_test)} samples")

    return X_train, X_val, X_test, y_train, y_val, y_test


def scale_features(X_train, X_val, X_test):
    """Scale features using StandardScaler"""
    print("\nScaling features...")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    print("✓ Features scaled")

    return X_train_scaled, X_val_scaled, X_test_scaled, scaler


def calculate_class_weights(y_train):
    """Calculate class weights for imbalanced dataset"""
    classes = np.unique(y_train)
    weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weight_dict = dict(zip(classes, weights))

    print(f"\nClass weights (for imbalanced data):")
    print(f"  Class 0 (no conflict): {class_weight_dict[0]:.2f}")
    print(f"  Class 1 (conflict): {class_weight_dict[1]:.2f}")

    return class_weight_dict


def train_random_forest(X_train, y_train, class_weights):
    """Train Random Forest classifier with optimized hyperparameters"""
    print("\nTraining Random Forest model...")

    # Optimized hyperparameters for maximum accuracy
    model = RandomForestClassifier(
        n_estimators=500,  # Many trees for better ensemble
        max_depth=25,  # Deep trees
        min_samples_split=2,  # Allow aggressive splits
        min_samples_leaf=1,  # Allow single-sample leaves
        max_features='sqrt',  # Feature subset per split
        class_weight=class_weights,  # Handle imbalance
        bootstrap=True,
        max_samples=0.8,  # Bootstrap 80% samples
        criterion='gini',  # Gini impurity
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=0  # Reduce output noise
    )

    # Train
    model.fit(X_train, y_train)

    print("✓ Model trained with 500 trees")

    return model


def evaluate_model(model, X, y, dataset_name=""):
    """Evaluate model performance"""
    print(f"\nEvaluating on {dataset_name}...")

    # Predictions
    y_pred = model.predict(X)
    y_pred_proba = model.predict_proba(X)[:, 1]

    # Metrics
    accuracy = accuracy_score(y, y_pred)
    precision = precision_score(y, y_pred, zero_division=0)
    recall = recall_score(y, y_pred, zero_division=0)
    f1 = f1_score(y, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y, y_pred_proba)

    # Confusion matrix
    cm = confusion_matrix(y, y_pred)
    tn, fp, fn, tp = cm.ravel()

    # Specificity
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    # Print results
    print(f"\n{dataset_name} Results:")
    print(f"  Accuracy:    {accuracy:.4f}")
    print(f"  Precision:   {precision:.4f}")
    print(f"  Recall:      {recall:.4f}")
    print(f"  F1-Score:    {f1:.4f}")
    print(f"  ROC-AUC:     {roc_auc:.4f}")
    print(f"  Specificity: {specificity:.4f}")

    print(f"\nConfusion Matrix:")
    print(f"  TN: {tn}  FP: {fp}")
    print(f"  FN: {fn}  TP: {tp}")

    # Return metrics
    return {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'roc_auc': float(roc_auc),
        'specificity': float(specificity),
        'confusion_matrix': {
            'tn': int(tn), 'fp': int(fp),
            'fn': int(fn), 'tp': int(tp)
        }
    }, y_pred, y_pred_proba


def plot_confusion_matrix(y_true, y_pred, save_path):
    """Plot and save confusion matrix"""
    cm = confusion_matrix(y_true, y_pred)

    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=True,
                xticklabels=['No Conflict', 'Conflict'],
                yticklabels=['No Conflict', 'Conflict'],
                annot_kws={'size': 14, 'weight': 'bold'})

    plt.title('Confusion Matrix - Test Set', fontsize=16, fontweight='bold', pad=20)
    plt.ylabel('True Label', fontsize=12, fontweight='bold')
    plt.xlabel('Predicted Label', fontsize=12, fontweight='bold')

    # Add accuracy text
    accuracy = (cm[0, 0] + cm[1, 1]) / cm.sum()
    plt.text(1, 2.3, f'Accuracy: {accuracy:.1%}',
             ha='center', fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved confusion matrix: {save_path}")


def plot_roc_curve(y_true, y_pred_proba, save_path):
    """Plot and save ROC curve"""
    fpr, tpr, thresholds = roc_curve(y_true, y_pred_proba)
    roc_auc = roc_auc_score(y_true, y_pred_proba)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=3,
             label=f'ROC Curve (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--',
             label='Random Classifier')

    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate', fontsize=12, fontweight='bold')
    plt.ylabel('True Positive Rate', fontsize=12, fontweight='bold')
    plt.title('ROC Curve - Test Set', fontsize=16, fontweight='bold', pad=20)
    plt.legend(loc="lower right", fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved ROC curve: {save_path}")


def plot_feature_importance(model, feature_names, save_path, top_n=15):
    """Plot and save feature importance (top N only)"""
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]

    plt.figure(figsize=(10, 8))
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, top_n))
    bars = plt.barh(range(top_n), importances[indices], color=colors)

    plt.yticks(range(top_n), [feature_names[i] for i in indices], fontsize=10)
    plt.xlabel('Feature Importance', fontsize=12, fontweight='bold')
    plt.title(f'Top {top_n} Most Important Features', fontsize=16, fontweight='bold', pad=20)
    plt.gca().invert_yaxis()

    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, importances[indices])):
        plt.text(val + 0.001, i, f'{val:.3f}',
                 va='center', fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ Saved feature importance: {save_path}")

    # Return full feature importance dict
    return {feature_names[i]: float(importances[i]) for i in range(len(feature_names))}


def save_model(model, scaler, metrics, feature_importance):
    """Save model, scaler, and metrics"""
    print("\nSaving model and results...")

    # Save model
    joblib.dump(model, RF_MODEL_PATH)
    print(f"✓ Model saved to: {RF_MODEL_PATH}")

    # Save scaler
    joblib.dump(scaler, SCALER_PATH)
    print(f"✓ Scaler saved to: {SCALER_PATH}")

    # Add feature importance to metrics
    metrics['feature_importance'] = feature_importance

    # Convert numpy types to native Python types for JSON serialization
    def convert_to_serializable(obj):
        if isinstance(obj, dict):
            return {str(k): convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    metrics = convert_to_serializable(metrics)

    # Save metrics
    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Metrics saved to: {METRICS_PATH}")


def main():
    """Main training pipeline"""
    print("=" * 60)
    print("Random Forest Model Training - OPTIMIZED")
    print("=" * 60 + "\n")

    # Create output directories first
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    # Load data
    df = load_training_data()
    if df is None:
        return

    # Prepare data
    X_train, X_val, X_test, y_train, y_val, y_test = prepare_data(df)

    # Get feature names
    feature_names = [col for col in df.columns if col != 'conflict']

    # Scale features
    X_train_scaled, X_val_scaled, X_test_scaled, scaler = scale_features(
        X_train, X_val, X_test
    )

    # Calculate class weights
    class_weights = calculate_class_weights(y_train)

    # Train model with optimized parameters
    model = train_random_forest(X_train_scaled, y_train, class_weights)

    # Evaluate on all sets
    train_metrics, train_pred, train_proba = evaluate_model(
        model, X_train_scaled, y_train, "Train Set"
    )
    val_metrics, val_pred, val_proba = evaluate_model(
        model, X_val_scaled, y_val, "Validation Set"
    )
    test_metrics, test_pred, test_proba = evaluate_model(
        model, X_test_scaled, y_test, "Test Set"
    )

    # Generate only 3 essential visualizations
    print("\nGenerating visualizations...")

    # 1. Confusion matrix (Test Set only)
    plot_confusion_matrix(y_test, test_pred,
                          os.path.join(PLOTS_DIR, 'confusion_matrix.png'))

    # 2. ROC curve (Test Set only)
    plot_roc_curve(y_test, test_proba,
                   os.path.join(PLOTS_DIR, 'roc_curve.png'))

    # 3. Feature importance (Top 15)
    feature_importance = plot_feature_importance(
        model, feature_names,
        os.path.join(PLOTS_DIR, 'feature_importance.png'),
        top_n=15
    )

    # Combine metrics
    all_metrics = {
        'train': train_metrics,
        'validation': val_metrics,
        'test': test_metrics,
        'model_params': {
            'n_estimators': 500,
            'max_depth': 25,
            'min_samples_split': 2,
            'min_samples_leaf': 1,
            'random_state': RANDOM_STATE
        }
    }

    # Save everything
    save_model(model, scaler, all_metrics, feature_importance)

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)

    # Summary box
    print(f"\n{'=' * 60}")
    print(f"{'FINAL MODEL PERFORMANCE (Test Set)':^60}")
    print(f"{'=' * 60}")
    print(f"  Accuracy:     {test_metrics['accuracy']:.2%}  (Overall correctness)")
    print(f"  Precision:    {test_metrics['precision']:.2%}  (Accuracy of conflict predictions)")
    print(f"  Recall:       {test_metrics['recall']:.2%}  (Catches actual conflicts)")
    print(f"  F1-Score:     {test_metrics['f1_score']:.2%}  (Balanced metric)")
    print(f"  ROC-AUC:      {test_metrics['roc_auc']:.2%}  (Discrimination ability)")
    print(f"{'=' * 60}")

    print(f"\n✓ Model trained with 500 trees")
    print(f"✓ 3 plots saved to: {PLOTS_DIR}")
    print(f"✓ Model ready for deployment!\n")


if __name__ == '__main__':
    main()