import joblib
import warnings
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.ensemble import RandomForestClassifier

try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

try:
    from imblearn.over_sampling import SMOTE
except ImportError:
    SMOTE = None  # type: ignore

warnings.filterwarnings("ignore")

# 1. Generate synthetic dataset
def generate_data(n=1000):
    np.random.seed(42)
    return pd.DataFrame({
        'amount': np.random.exponential(scale=200, size=n).round(2),
        'payment_method': np.random.choice(['CARD', 'UPI', 'NETBANKING'], n),
        'device_type': np.random.choice(['MOBILE', 'DESKTOP'], n),
        'hour': np.random.randint(0, 24, n),
        'is_fraud': np.random.choice([0, 1], size=n, p=[0.95, 0.05])
    })

# 2. Preprocessor builder
def build_preprocessor(X):
    num = X.select_dtypes(include=[np.number]).columns.tolist()
    cat = X.select_dtypes(exclude=[np.number]).columns.tolist()
    return ColumnTransformer([
        ("num", StandardScaler(), num),
        ("cat", OneHotEncoder(handle_unknown='ignore'), cat)
    ])

# 3. Get model
def get_model(name="rf"):
    if name == "xgb" and XGB_AVAILABLE:
        return XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, n_jobs=-1)
    return RandomForestClassifier(n_estimators=300, random_state=42)

# 4. Train with correct SMOTE pipeline
def train(X, y, preprocessor, model):
    # Preprocess first
    X_processed = preprocessor.fit_transform(X)

    # Apply SMOTE after encoding
    if SMOTE is not None:
        sm = SMOTE(random_state=42)
        X_processed, y = sm.fit_resample(X_processed, y)

    # Fit final model on processed data
    clf = model.fit(X_processed, y)

    # Save preprocessor inside a pipeline
    pipe = Pipeline([("prep", preprocessor), ("clf", model)])
    return pipe

# 5. Evaluate
def evaluate(pipe, X_test, y_test):
    X_proc = pipe.named_steps["prep"].transform(X_test)
    model = pipe.named_steps["clf"]
    y_pred = model.predict(X_proc)
    y_prob = model.predict_proba(X_proc)[:, 1]
    print(classification_report(y_test, y_pred))
    print("ROC AUC:", roc_auc_score(y_test, y_prob))

# 6. Main runner
def main():
    df = generate_data()
    X = df.drop(columns=["is_fraud"])
    y = df["is_fraud"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.25)

    print("✔ Building pipeline")
    preprocessor = build_preprocessor(X_train)
    model = get_model("rf")

    print("✔ Training model")
    pipe = train(X_train, y_train, preprocessor, model)

    print("✔ Evaluating model")
    evaluate(pipe, X_test, y_test)

    print("✔ Saving model")
    joblib.dump(pipe, "fraud_model.pkl")

if _name_ == "_main_":
    main()
