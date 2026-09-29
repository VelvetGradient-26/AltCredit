"""
Alternative Credit Scoring - Model & Hyperparameter Search

Runs 5-fold GridSearchCV across:
    1. Logistic Regression
    2. Random Forest
    3. Extra Trees
    4. Gradient Boosting
    5. HistGradientBoosting
    6. XGBoost

Primary optimization metric:
    ROC-AUC

Also reports:
    Accuracy
    Precision
    Recall
    F1
    ROC-AUC
    PR-AUC
    Brier Score

Dataset:
    data/processed/ml_training_dataset_model_A_realistic_calibrated_v2_5500.csv
"""

from pathlib import Path
import warnings
import time

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

from sklearn.model_selection import GridSearchCV, StratifiedKFold

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
)

from sklearn.metrics import make_scorer
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "ml_training_dataset_model_A_realistic_balanced_5500.csv"
)

OUTPUT_DIR = BASE_DIR / "gridsearch_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FEATURES
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
    # Behaviour
    # --------------------------------------------------------

    "positive_habits",
    "risk_flags",
]

TARGET = "borrower_outcome"


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 80)
print("ALTERNATIVE CREDIT SCORING - GRID SEARCH")
print("=" * 80)

print(f"\nDataset:\n{DATA_PATH}")

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"\nDataset not found:\n{DATA_PATH}\n\n"
        "Check that your CSV filename/path is correct."
    )

df = pd.read_csv(DATA_PATH)

print(f"\nDataset shape: {df.shape}")

print("\nTarget distribution:")
print(df[TARGET].value_counts())

print("\nTarget percentage:")
print(
    df[TARGET]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)


# ============================================================
# X / y
# ============================================================

X = df[FEATURES].copy()
y = df[TARGET].copy()


# ============================================================
# FEATURE TYPES
# ============================================================

CATEGORICAL_FEATURES = [
    "education_level",
    "employment_status",
    "housing",
    "education",
]

NUMERICAL_FEATURES = [
    feature
    for feature in FEATURES
    if feature not in CATEGORICAL_FEATURES
]


# ============================================================
# PREPROCESSING
# ============================================================

numeric_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="median")
        ),
        (
            "scaler",
            StandardScaler()
        ),
    ]
)


categorical_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="most_frequent")
        ),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False
            )
        ),
    ]
)


preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            numeric_pipeline,
            NUMERICAL_FEATURES
        ),
        (
            "categorical",
            categorical_pipeline,
            CATEGORICAL_FEATURES
        ),
    ]
)


# ============================================================
# CROSS VALIDATION
# ============================================================

CV = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)


# ============================================================
# MODELS + HYPERPARAMETER GRIDS
# ============================================================

models = {

    # --------------------------------------------------------
    # 1. Logistic Regression
    # --------------------------------------------------------

    "LogisticRegression": {

        "model": LogisticRegression(
            max_iter=3000,
            class_weight="balanced",
            random_state=42
        ),

        "params": {

            "model__C": [
                0.01,
                0.1,
                1,
                10
            ],

            "model__solver": [
                "lbfgs",
                "liblinear"
            ],

        },
    },


    # --------------------------------------------------------
    # 2. Random Forest
    # --------------------------------------------------------

    "RandomForest": {

        "model": RandomForestClassifier(
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ),

        "params": {

            "model__n_estimators": [
                300,
                600
            ],

            "model__max_depth": [
                None,
                8,
                15
            ],

            "model__min_samples_leaf": [
                1,
                3,
                5
            ],

            "model__max_features": [
                "sqrt",
                0.7
            ],
        },
    },


    # --------------------------------------------------------
    # 3. Extra Trees
    # --------------------------------------------------------

    "ExtraTrees": {

        "model": ExtraTreesClassifier(
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ),

        "params": {

            "model__n_estimators": [
                300,
                600
            ],

            "model__max_depth": [
                None,
                8,
                15
            ],

            "model__min_samples_leaf": [
                1,
                3,
                5
            ],

            "model__max_features": [
                "sqrt",
                0.7
            ],
        },
    },


    # --------------------------------------------------------
    # 4. Gradient Boosting
    # --------------------------------------------------------

    "GradientBoosting": {

        "model": GradientBoostingClassifier(
            random_state=42
        ),

        "params": {

            "model__n_estimators": [
                100,
                200
            ],

            "model__learning_rate": [
                0.03,
                0.05,
                0.1
            ],

            "model__max_depth": [
                2,
                3
            ],

            "model__min_samples_leaf": [
                3,
                8
            ],
        },
    },


    # --------------------------------------------------------
    # 5. HistGradientBoosting
    # --------------------------------------------------------

    "HistGradientBoosting": {

        "model": HistGradientBoostingClassifier(
            random_state=42
        ),

        "params": {

            "model__max_iter": [
                100,
                200
            ],

            "model__learning_rate": [
                0.03,
                0.05,
                0.1
            ],

            "model__max_leaf_nodes": [
                15,
                31
            ],

            "model__l2_regularization": [
                0,
                1
            ],
        },
    },


    # --------------------------------------------------------
    # 6. XGBoost
    # --------------------------------------------------------

    "XGBoost": {

        "model": XGBClassifier(

            objective="binary:logistic",

            eval_metric="logloss",

            random_state=42,

            n_jobs=-1,

            tree_method="hist",
        ),

        "params": {

            "model__n_estimators": [
                200,
                400
            ],

            "model__max_depth": [
                2,
                3,
                4
            ],

            "model__learning_rate": [
                0.03,
                0.05,
                0.1
            ],

            "model__min_child_weight": [
                1,
                5
            ],

            "model__subsample": [
                0.8,
                1.0
            ],

            "model__colsample_bytree": [
                0.8,
                1.0
            ],

            "model__reg_alpha": [
                0,
                0.1
            ],

            "model__reg_lambda": [
                1,
                2
            ],
        },
    },
}


# ============================================================
# SCORING
# ============================================================

SCORING = {
    "accuracy": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "roc_auc": "roc_auc",
    "pr_auc": "average_precision",
    "brier": "neg_brier_score",
}


# ============================================================
# RUN GRID SEARCH
# ============================================================

all_results = []
best_results = []


for model_name, config in models.items():

    print("\n")
    print("=" * 80)
    print(f"MODEL: {model_name}")
    print("=" * 80)

    model = config["model"]
    param_grid = config["params"]

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    # Count combinations
    from sklearn.model_selection import ParameterGrid

    n_combinations = len(
        list(ParameterGrid(param_grid))
    )

    print(
        f"\nHyperparameter combinations: "
        f"{n_combinations}"
    )

    print(
        f"Total CV fits: "
        f"{n_combinations * CV.n_splits}"
    )

    start_time = time.time()

    search = GridSearchCV(

        estimator=pipeline,

        param_grid=param_grid,

        scoring="roc_auc",

        cv=CV,

        n_jobs=-1,

        refit=True,

        return_train_score=False,

        verbose=1,
    )

    search.fit(X, y)

    elapsed = time.time() - start_time

    print(
        f"\nCompleted in "
        f"{elapsed / 60:.2f} minutes"
    )

    print(
        f"\nBest ROC-AUC: "
        f"{search.best_score_:.5f}"
    )

    print("\nBest parameters:")

    for key, value in search.best_params_.items():
        print(f"  {key}: {value}")


    # --------------------------------------------------------
    # Extract CV results
    # --------------------------------------------------------

    results = pd.DataFrame(
        search.cv_results_
    )

    results["model"] = model_name

    results["best"] = (
        results["rank_test_score"] == 1
    )

    # Convert Brier from negative scoring
    results["mean_brier"] = (
        -results["mean_test_score"]
        if False
        else np.nan
    )

    # --------------------------------------------------------
    # We need the other metrics for every configuration.
    #
    # Instead of rerunning every configuration with
    # cross_validate, we retain GridSearchCV's primary
    # ROC-AUC search results here.
    #
    # The best configuration will subsequently be evaluated
    # using all metrics.
    # --------------------------------------------------------

    result_rows = []

    for i, row in results.iterrows():

        result_rows.append({

            "model": model_name,

            "rank": int(
                row["rank_test_score"]
            ),

            "mean_roc_auc": row[
                "mean_test_score"
            ],

            "std_roc_auc": row[
                "std_test_score"
            ],

            "params": str(
                row["params"]
            ),

        })

    model_results = pd.DataFrame(
        result_rows
    )

    all_results.append(
        model_results
    )


    # --------------------------------------------------------
    # Evaluate BEST model with all metrics
    # --------------------------------------------------------

    best_pipeline = search.best_estimator_

    from sklearn.model_selection import cross_validate

    detailed_scores = cross_validate(

        best_pipeline,

        X,

        y,

        cv=CV,

        scoring=SCORING,

        n_jobs=-1,

        return_train_score=False,
    )

    best_row = {

        "model": model_name,

        "mean_accuracy":
            detailed_scores[
                "test_accuracy"
            ].mean(),

        "std_accuracy":
            detailed_scores[
                "test_accuracy"
            ].std(),

        "mean_precision":
            detailed_scores[
                "test_precision"
            ].mean(),

        "std_precision":
            detailed_scores[
                "test_precision"
            ].std(),

        "mean_recall":
            detailed_scores[
                "test_recall"
            ].mean(),

        "std_recall":
            detailed_scores[
                "test_recall"
            ].std(),

        "mean_f1":
            detailed_scores[
                "test_f1"
            ].mean(),

        "std_f1":
            detailed_scores[
                "test_f1"
            ].std(),

        "mean_roc_auc":
            detailed_scores[
                "test_roc_auc"
            ].mean(),

        "std_roc_auc":
            detailed_scores[
                "test_roc_auc"
            ].std(),

        "mean_pr_auc":
            detailed_scores[
                "test_pr_auc"
            ].mean(),

        "std_pr_auc":
            detailed_scores[
                "test_pr_auc"
            ].std(),

        "mean_brier":
            -detailed_scores[
                "test_brier"
            ].mean(),

        "std_brier":
            detailed_scores[
                "test_brier"
            ].std(),

        "best_params":
            str(search.best_params_),

        "search_time_minutes":
            elapsed / 60,
    }

    best_results.append(best_row)


# ============================================================
# SAVE RESULTS
# ============================================================

all_results_df = pd.concat(
    all_results,
    ignore_index=True
)

all_results_df = all_results_df.sort_values(
    by=[
        "mean_roc_auc",
    ],
    ascending=False
)

all_results_df.insert(
    0,
    "overall_rank",
    range(1, len(all_results_df) + 1)
)


best_results_df = pd.DataFrame(
    best_results
)

best_results_df = best_results_df.sort_values(
    by=[
        "mean_roc_auc",
        "mean_pr_auc",
        "mean_f1",
    ],
    ascending=False
)

best_results_df.insert(
    0,
    "model_rank",
    range(1, len(best_results_df) + 1)
)


# ============================================================
# SAVE CSV FILES
# ============================================================

all_results_path = (
    OUTPUT_DIR
    / "gridsearch_all_results.csv"
)

best_results_path = (
    OUTPUT_DIR
    / "gridsearch_best_models.csv"
)


all_results_df.to_csv(
    all_results_path,
    index=False
)

best_results_df.to_csv(
    best_results_path,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

summary_path = (
    OUTPUT_DIR
    / "gridsearch_summary.txt"
)

with open(
    summary_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "ALTERNATIVE CREDIT SCORING - GRID SEARCH\n"
    )

    f.write(
        "=" * 80 + "\n\n"
    )

    f.write(
        f"Dataset: {DATA_PATH}\n"
    )

    f.write(
        f"Rows: {len(df)}\n"
    )

    f.write(
        f"Features: {len(FEATURES)}\n"
    )

    f.write(
        "CV: Stratified 5-Fold\n"
    )

    f.write(
        "Primary metric: ROC-AUC\n\n"
    )

    f.write(
        "BEST MODEL PER ALGORITHM\n"
    )

    f.write(
        "=" * 80 + "\n\n"
    )

    f.write(
        best_results_df.to_string(
            index=False
        )
    )


# ============================================================
# PRINT FINAL RESULTS
# ============================================================

print("\n\n")
print("=" * 80)
print("FINAL MODEL COMPARISON")
print("=" * 80)

display_columns = [

    "model_rank",
    "model",
    "mean_accuracy",
    "mean_precision",
    "mean_recall",
    "mean_f1",
    "mean_roc_auc",
    "mean_pr_auc",
    "mean_brier",
]

print(
    best_results_df[
        display_columns
    ].round(4).to_string(
        index=False
    )
)


print("\n")
print("=" * 80)
print("FILES GENERATED")
print("=" * 80)

print(
    f"\nDetailed results:\n"
    f"{all_results_path}"
)

print(
    f"\nBest model comparison:\n"
    f"{best_results_path}"
)

print(
    f"\nSummary:\n"
    f"{summary_path}"
)

print("\nDone.")