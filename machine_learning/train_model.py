# ============================================================
# ALTERNATIVE CREDIT SCORING - ML TRAINING PIPELINE
# ============================================================
#
# Models:
#   1. Logistic Regression - baseline
#   2. XGBoost             - main nonlinear model
#
# Includes:
#   - Data loading
#   - Feature selection
#   - Categorical encoding
#   - Train/test split
#   - Model training
#   - Evaluation
#   - Confusion matrix
#   - Feature importance
#   - SHAP explainability
#   - Probability of Default
#   - Alternative Credit Score
#   - Model saving
#
# ============================================================

import json
import joblib
import numpy as np
import pandas as pd

from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    classification_report
)

from xgboost import XGBClassifier

import shap
import matplotlib.pyplot as plt


# ============================================================
# 1. PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "ml_training_dataset_model_A_realistic_balanced_5500.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "models"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. LOAD DATASET
# ============================================================

print("\n" + "=" * 70)
print("ALTERNATIVE CREDIT SCORING - ML PIPELINE")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(DATA_PATH)

print(f"Dataset shape: {df.shape}")


# ============================================================
# 3. BASIC DATA VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("DATA VALIDATION")
print("=" * 70)

print("\nMissing values:")

missing = df.isnull().sum()

print(
    missing[missing > 0]
    if missing.sum() > 0
    else "No missing values"
)

print("\nTarget distribution:")

print(
    df["target_class"].value_counts()
)

print("\nTarget percentages:")

print(
    (
        df["target_class"]
        .value_counts(normalize=True)
        * 100
    ).round(2)
)


# ============================================================
# 4. FEATURE SELECTION
# ============================================================
#
# IMPORTANT:
#
# We use the complete set of legitimate borrower features.
#
# We DO NOT use:
#
#   user_id
#   applicant_id
#   match_cost
#   risk_index
#   borrower_outcome -> TARGET
#   target_class     -> duplicate TARGET
#
# risk_index is especially important because it was used
# during synthetic target generation. Using it would cause
# target leakage.
#
# ============================================================


FEATURES = [

    # --------------------------------------------------------
    # Lifestyle
    # --------------------------------------------------------

    "age",
    "education_level",
    "employment_status",
    "monthly_income",
    "city_tier",
    "months_at_job",
    "housing",
    "rent_on_time_months",
    "digital_payment_rate",
    "education",

    # --------------------------------------------------------
    # Spending Behaviour
    # --------------------------------------------------------

    "monthly_spend",
    "essential_pct",
    "cashflow_volatility",
    "savings_days",

    # --------------------------------------------------------
    # Repayment Discipline
    # --------------------------------------------------------

    "on_time_rate",
    "dti",
    "credit_util",

    # --------------------------------------------------------
    # Delinquency
    # --------------------------------------------------------

    "delinq_90plus",
    "delinq_60plus",
    "delinq_30plus",

    # --------------------------------------------------------
    # Behavioural Signals
    # --------------------------------------------------------

    "positive_habits",
    "risk_flags"
]


TARGET = "borrower_outcome"


X = df[FEATURES].copy()

y = df[TARGET].astype(int)


print("\nNumber of ML features:", len(FEATURES))

print("\nFeatures:")

for feature in FEATURES:

    print("  -", feature)


# ============================================================
# 5. DEFINE CATEGORICAL / NUMERICAL FEATURES
# ============================================================


CATEGORICAL_FEATURES = [

    "education_level",
    "employment_status",
    "housing",
    "education"

]


NUMERICAL_FEATURES = [

    feature

    for feature in FEATURES

    if feature not in CATEGORICAL_FEATURES

]


# ============================================================
# 6. PREPROCESSING
# ============================================================

print("\n" + "=" * 70)
print("PREPROCESSING")
print("=" * 70)


# Numerical preprocessing

numeric_transformer = Pipeline(
    steps=[

        (
            "imputer",
            SimpleImputer(
                strategy="median"
            )
        ),

        (
            "scaler",
            StandardScaler()
        )

    ]
)


# Categorical preprocessing

categorical_transformer = Pipeline(
    steps=[

        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            )
        ),

        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False
            )
        )

    ]
)


# Combine preprocessing

preprocessor = ColumnTransformer(
    transformers=[

        (
            "num",
            numeric_transformer,
            NUMERICAL_FEATURES
        ),

        (
            "cat",
            categorical_transformer,
            CATEGORICAL_FEATURES
        )

    ]
)


# ============================================================
# 7. TRAIN / TEST SPLIT
# ============================================================

print("\n" + "=" * 70)
print("TRAIN / TEST SPLIT")
print("=" * 70)


X_train, X_test, y_train, y_test = train_test_split(

    X,
    y,

    test_size=0.20,

    random_state=42,

    stratify=y

)


print(
    f"\nTraining samples: {len(X_train)}"
)

print(
    f"Testing samples : {len(X_test)}"
)


# ============================================================
# 8. LOGISTIC REGRESSION BASELINE
# ============================================================

print("\n" + "=" * 70)
print("TRAINING LOGISTIC REGRESSION")
print("=" * 70)


logistic_model = Pipeline(

    steps=[

        (
            "preprocessor",
            preprocessor
        ),

        (
            "model",

            LogisticRegression(

                max_iter=2000,

                class_weight="balanced",

                random_state=42

            )
        )

    ]

)


logistic_model.fit(

    X_train,

    y_train

)


print(
    "Logistic Regression training completed."
)


# ============================================================
# 9. LOGISTIC REGRESSION PREDICTIONS
# ============================================================


logistic_probability = (

    logistic_model
    .predict_proba(X_test)[:, 1]

)


logistic_prediction = (

    logistic_probability >= 0.50

).astype(int)


# ============================================================
# 10. PREPROCESS DATA FOR XGBOOST
# ============================================================

print("\n" + "=" * 70)
print("PREPARING DATA FOR XGBOOST")
print("=" * 70)


X_train_encoded = (

    preprocessor
    .fit_transform(X_train)

)


X_test_encoded = (

    preprocessor
    .transform(X_test)

)


print(
    "\nEncoded training shape:",
    X_train_encoded.shape
)

print(
    "Encoded testing shape:",
    X_test_encoded.shape
)


# ============================================================
# 11. XGBOOST MODEL
# ============================================================

print("\n" + "=" * 70)
print("TRAINING XGBOOST")
print("=" * 70)


xgb_model = XGBClassifier(

    n_estimators=300,

    max_depth=4,

    learning_rate=0.035,

    min_child_weight=5,

    subsample=0.85,

    colsample_bytree=0.85,

    reg_alpha=0.10,

    reg_lambda=2.0,

    objective="binary:logistic",

    eval_metric="logloss",

    random_state=42,

    n_jobs=-1

)


xgb_model.fit(

    X_train_encoded,

    y_train

)


print(
    "XGBoost training completed."
)


# ============================================================
# 12. XGBOOST PREDICTIONS
# ============================================================


xgb_probability = (

    xgb_model
    .predict_proba(X_test_encoded)[:, 1]

)


xgb_prediction = (

    xgb_probability >= 0.50

).astype(int)


# ============================================================
# 13. EVALUATION FUNCTION
# ============================================================


def evaluate_model(

    model_name,

    y_true,

    predictions,

    probabilities

):

    cm = confusion_matrix(

        y_true,

        predictions

    )

    return {

        "model": model_name,

        "accuracy":
            accuracy_score(
                y_true,
                predictions
            ),

        "precision":
            precision_score(
                y_true,
                predictions
            ),

        "recall":
            recall_score(
                y_true,
                predictions
            ),

        "f1":
            f1_score(
                y_true,
                predictions
            ),

        "roc_auc":
            roc_auc_score(
                y_true,
                probabilities
            ),

        "pr_auc":
            average_precision_score(
                y_true,
                probabilities
            ),

        "brier_score":
            brier_score_loss(
                y_true,
                probabilities
            ),

        "true_negative":
            int(cm[0][0]),

        "false_positive":
            int(cm[0][1]),

        "false_negative":
            int(cm[1][0]),

        "true_positive":
            int(cm[1][1])

    }


# ============================================================
# 14. COMPARE MODELS
# ============================================================


results = pd.DataFrame([

    evaluate_model(

        "Logistic Regression",

        y_test,

        logistic_prediction,

        logistic_probability

    ),

    evaluate_model(

        "XGBoost",

        y_test,

        xgb_prediction,

        xgb_probability

    )

])


print("\n" + "=" * 70)
print("MODEL COMPARISON")
print("=" * 70)

print(

    results.round(4)
    .to_string(index=False)

)


# Save results

results.to_csv(

    OUTPUT_DIR
    / "model_comparison.csv",

    index=False

)


# ============================================================
# 15. XGBOOST CLASSIFICATION REPORT
# ============================================================


print("\n" + "=" * 70)
print("XGBOOST CLASSIFICATION REPORT")
print("=" * 70)


print(

    classification_report(

        y_test,

        xgb_prediction,

        target_names=[

            "Successful Borrower",

            "Defaulted"

        ]

    )

)


# ============================================================
# 16. CONFUSION MATRIX
# ============================================================


cm = confusion_matrix(

    y_test,

    xgb_prediction

)


print("\nConfusion Matrix:")

print(cm)


# ============================================================
# 17. FEATURE IMPORTANCE
# ============================================================


print("\n" + "=" * 70)
print("XGBOOST FEATURE IMPORTANCE")
print("=" * 70)


feature_names = (

    preprocessor
    .get_feature_names_out()

)


feature_importance = pd.DataFrame({

    "feature":
        feature_names,

    "importance":
        xgb_model.feature_importances_

})


feature_importance = (

    feature_importance
    .sort_values(
        "importance",
        ascending=False
    )

)


print(

    feature_importance
    .head(20)
    .round(4)
    .to_string(index=False)

)


feature_importance.to_csv(

    OUTPUT_DIR
    / "xgboost_feature_importance.csv",

    index=False

)


# ============================================================
# 18. SHAP EXPLAINABILITY
# ============================================================

print("\n" + "=" * 70)
print("GENERATING SHAP EXPLANATIONS")
print("=" * 70)


explainer = shap.TreeExplainer(

    xgb_model

)


shap_values = explainer.shap_values(

    X_test_encoded

)


# ------------------------------------------------------------
# Global SHAP importance
# ------------------------------------------------------------


shap_importance = pd.DataFrame({

    "feature":
        feature_names,

    "mean_abs_shap":
        np.abs(shap_values)
        .mean(axis=0)

})


shap_importance = (

    shap_importance
    .sort_values(
        "mean_abs_shap",
        ascending=False
    )

)


print("\nTop SHAP features:")

print(

    shap_importance
    .head(20)
    .round(4)
    .to_string(index=False)

)


shap_importance.to_csv(

    OUTPUT_DIR
    / "xgboost_shap_importance.csv",

    index=False

)


# ============================================================
# 19. SHAP SUMMARY PLOT
# ============================================================


plt.figure()

shap.summary_plot(

    shap_values,

    X_test_encoded,

    feature_names=feature_names,

    plot_type="bar",

    show=False

)

plt.tight_layout()

plt.savefig(

    OUTPUT_DIR
    / "shap_summary.png",

    dpi=200,

    bbox_inches="tight"

)

plt.close()


# ============================================================
# 20. SHAP BEESWARM
# ============================================================


plt.figure()

shap.summary_plot(

    shap_values,

    X_test_encoded,

    feature_names=feature_names,

    show=False

)

plt.tight_layout()

plt.savefig(

    OUTPUT_DIR
    / "shap_beeswarm.png",

    dpi=200,

    bbox_inches="tight"

)

plt.close()


# ============================================================
# 21. GENERATE CREDIT SCORES
# ============================================================

print("\n" + "=" * 70)
print("GENERATING ALTERNATIVE CREDIT SCORES")
print("=" * 70)


# Probability of default

probability_of_default = xgb_probability


# Credit score
#
# PD = 0.00  -> Score 1000
# PD = 0.25  -> Score 750
# PD = 0.50  -> Score 500
# PD = 1.00  -> Score 0
#

credit_score = (

    1000
    * (1 - probability_of_default)

)


credit_score = np.clip(

    credit_score,

    0,

    1000

)


credit_score = (

    credit_score
    .round()
    .astype(int)

)


# ============================================================
# 22. RISK TIER
# ============================================================


def get_risk_tier(score):

    if score >= 750:

        return "Prime / Low Risk"

    elif score >= 650:

        return "Near-Prime / Medium Risk"

    elif score >= 550:

        return "Sub-Prime / Fair"

    else:

        return "High Risk / Poor"


risk_tier = [

    get_risk_tier(score)

    for score in credit_score

]


# ============================================================
# 23. SAVE PREDICTIONS
# ============================================================


prediction_output = X_test.copy()


prediction_output["actual_outcome"] = (

    y_test.values

)


prediction_output["probability_of_default"] = (

    probability_of_default

)


prediction_output["predicted_outcome"] = (

    xgb_prediction

)


prediction_output["credit_score"] = (

    credit_score

)


prediction_output["risk_tier"] = (

    risk_tier

)


prediction_output.to_csv(

    OUTPUT_DIR
    / "credit_score_predictions.csv",

    index=False

)


# ============================================================
# 24. SAVE TRAINED MODELS
# ============================================================


joblib.dump(

    {

        "preprocessor":
            preprocessor,

        "model":
            xgb_model,

        "features":
            FEATURES,

        "target":
            TARGET

    },

    OUTPUT_DIR
    / "xgboost_credit_model.joblib"

)


joblib.dump(

    logistic_model,

    OUTPUT_DIR
    / "logistic_regression_model.joblib"

)


# ============================================================
# 25. SAVE MODEL METADATA
# ============================================================


metadata = {

    "dataset":
        str(DATA_PATH),

    "records":
        int(len(df)),

    "features":
        FEATURES,

    "categorical_features":
        CATEGORICAL_FEATURES,

    "numerical_features":
        NUMERICAL_FEATURES,

    "target":
        TARGET,

    "train_size":
        int(len(X_train)),

    "test_size":
        int(len(X_test)),

    "credit_score_formula":
        "1000 * (1 - probability_of_default)",

    "risk_tiers": {

        "750-1000":
            "Prime / Low Risk",

        "650-749":
            "Near-Prime / Medium Risk",

        "550-649":
            "Sub-Prime / Fair",

        "0-549":
            "High Risk / Poor"

    },

    "excluded_features": [

        "user_id",

        "applicant_id",

        "match_cost",

        "risk_index",

        "borrower_outcome",

        "target_class"

    ]

}


with open(

    OUTPUT_DIR
    / "model_metadata.json",

    "w"

) as file:

    json.dump(

        metadata,

        file,

        indent=4

    )


# ============================================================
# 26. SHOW SAMPLE RESULTS
# ============================================================


print("\n" + "=" * 70)
print("SAMPLE CREDIT SCORES")
print("=" * 70)


sample_results = prediction_output[
    [
        "probability_of_default",
        "credit_score",
        "risk_tier"
    ]
].head(10)


print(

    sample_results.to_string(
        index=False
    )

)


# ============================================================
# 27. COMPLETE
# ============================================================


print("\n" + "=" * 70)
print("TRAINING COMPLETE")
print("=" * 70)


print("\nGenerated files:")

for file in sorted(OUTPUT_DIR.iterdir()):

    print(
        "  ✓",
        file.name
    )


print("\nMain model:")

print(

    OUTPUT_DIR
    / "xgboost_credit_model.joblib"

)

print("\nCredit score formula:")

print(

    "Credit Score = 1000 × (1 - Probability of Default)"

)

print("\nDone.")

print("\nPD DISTRIBUTION")
print("=" * 50)

pd_series = pd.Series(
    xgb_probability,
    name="PD"
)

print(pd_series.describe(
    percentiles=[
        0.01,
        0.05,
        0.10,
        0.25,
        0.50,
        0.75,
        0.90,
        0.95,
        0.99
    ]
))

print("\nPD buckets:")

print(
    pd.cut(
        pd_series,
        bins=[
            0,
            0.05,
            0.10,
            0.20,
            0.30,
            0.50,
            1.00
        ]
    ).value_counts()
    .sort_index()
)