import pandas as pd
import numpy as np
from datetime import timedelta
import joblib
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
import warnings
import os
import re

warnings.filterwarnings("ignore")

# Directory where model artifacts live alongside this script
AI_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Personalization hyper-parameters
# ---------------------------------------------------------------------------
# Minimum days of user-specific history required to switch on each tier.
_MIN_DAYS_FOR_FINETUNE = 45   # Tier 2: user scaler + fine-tuned LSTM
_FINETUNE_LR = 5e-5           # Very low LR — prevents catastrophic forgetting
_FINETUNE_EPOCHS = 20         # Max epochs (early-stopping usually fires sooner)
_FINETUNE_HISTORY = 120       # Use at most the last N days for fine-tuning
_MAX_PROJECTION_DAYS = 30     # Hard cap on multi-day cumulative projection


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------

def _category_model_key(category: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", str(category).strip())
    key = re.sub(r"_+", "_", key).strip("_")
    return key or "Uncategorized"


def _resolve_model_paths(category: str) -> dict[str, str]:
    category_key = _category_model_key(category)
    prefix_candidates = [f"GLOBAL_{category_key}", f"GLOBAL_{category}"]

    for prefix in prefix_candidates:
        model_path_lstm = os.path.join(AI_DIR, f"lstm_{prefix}.keras")
        model_path_xgb  = os.path.join(AI_DIR, f"xgb_{prefix}.pkl")
        scaler_path      = os.path.join(AI_DIR, f"scaler_{prefix}.pkl")
        accounts_path    = os.path.join(AI_DIR, f"accounts_{prefix}.pkl")
        meta_path        = os.path.join(AI_DIR, f"meta_{prefix}.pkl")

        if all(
            os.path.exists(p)
            for p in [model_path_lstm, model_path_xgb, scaler_path, accounts_path]
        ):
            return {
                "prefix": prefix,
                "model_path_lstm": model_path_lstm,
                "model_path_xgb": model_path_xgb,
                "scaler_path": scaler_path,
                "accounts_path": accounts_path,
                "meta_path": meta_path,
            }

    raise FileNotFoundError(f"Models for category '{category}' not found.")


# ---------------------------------------------------------------------------
# User series builder
# ---------------------------------------------------------------------------

def _build_category_series_for_user(
    df: pd.DataFrame,
    user_id: str,
    category: str,
) -> pd.Series:
    """
    Build a daily spending time-series for (user_id, category).

    Priority:
      1. User's own transactions (personalized series).
      2. Cross-user mean for the category (fallback when user has no history).
    """
    daily_spend = (
        df.groupby(["account_id", "date", "category"])["amount"]
        .sum()
        .reset_index()
    )
    category_daily = daily_spend[daily_spend["category"] == category]

    if category_daily.empty:
        return pd.Series(dtype=float)

    user_data = category_daily[
        category_daily["account_id"].astype(str) == str(user_id)
    ]

    if not user_data.empty:
        series = user_data.set_index("date")["amount"].sort_index()
    else:
        # Fallback: global cross-user average for this category
        panel = category_daily.pivot(
            index="date", columns="account_id", values="amount"
        ).fillna(0)
        series = panel.mean(axis=1)

    full_dates = pd.date_range(series.index.min(), series.index.max(), freq="D")
    series = series.reindex(full_dates).fillna(0.0).astype(float)
    return series


# ---------------------------------------------------------------------------
# Personalization: Tier 2 — user-specific scaler + LSTM fine-tuning
# ---------------------------------------------------------------------------

def _fit_user_scaler(series_values: np.ndarray) -> MinMaxScaler:
    """
    Fit a MinMaxScaler on the user's own spending history.

    feature_range=(0.05, 0.95) leaves head-room so values slightly outside
    the historical range do not saturate the scaler during projection rollouts.
    """
    scaler = MinMaxScaler(feature_range=(0.05, 0.95))
    scaler.fit(series_values.reshape(-1, 1))
    return scaler


def _fine_tune_lstm_for_user(
    lstm_model: tf.keras.Model,
    user_series_values: np.ndarray,
    user_scaler: MinMaxScaler,
    look_back: int,
) -> tf.keras.Model:
    """
    Transfer-learning fine-tune: clone the global LSTM and adapt it to a
    specific user's spending patterns.

    Architecture decision
    ─────────────────────
    • First LSTM layer  → FROZEN   (general temporal patterns from all users)
    • Second LSTM layer → TRAINABLE (user-specific sequential dynamics)
    • Dense layers      → TRAINABLE (user-specific output mapping)

    This retains the broad knowledge from global training while allowing
    the upper layers to specialize for the individual user.
    """
    # Work on recent history only to keep fine-tuning fast
    recent_values = user_series_values[-_FINETUNE_HISTORY:]
    scaled = user_scaler.transform(recent_values.reshape(-1, 1)).reshape(-1)

    # Build sequence windows
    X_list, y_list = [], []
    for i in range(look_back, len(scaled)):
        X_list.append(scaled[i - look_back: i])
        y_list.append(scaled[i])

    if len(X_list) < 10:
        # Not enough windows even with sufficient raw data — skip fine-tuning
        return lstm_model

    X = np.array(X_list).reshape(-1, look_back, 1)
    y = np.array(y_list)

    # Clone so the shared global model weights are never mutated
    user_model = tf.keras.models.clone_model(lstm_model)
    user_model.set_weights(lstm_model.get_weights())

    # Layer-wise freezing
    lstm_seen = 0
    for layer in user_model.layers:
        if isinstance(layer, tf.keras.layers.LSTM):
            lstm_seen += 1
            layer.trainable = lstm_seen > 1   # freeze 1st, unfreeze 2nd
        elif isinstance(layer, tf.keras.layers.Dense):
            layer.trainable = True

    user_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=_FINETUNE_LR),
        loss=tf.keras.losses.Huber(delta=1.0),
    )

    user_model.fit(
        X,
        y,
        epochs=_FINETUNE_EPOCHS,
        batch_size=min(8, max(1, len(X))),
        shuffle=False,
        verbose=0,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="loss",
                patience=5,
                restore_best_weights=True,
                min_delta=1e-5,
            )
        ],
    )

    return user_model


# ---------------------------------------------------------------------------
# Multi-step autoregressive projection
# ---------------------------------------------------------------------------

def _project_cumulative_spend(
    active_model: tf.keras.Model,
    active_scaler: MinMaxScaler,
    last_window_raw: np.ndarray,
    look_back: int,
    days_to_project: int,
) -> float:
    """
    Auto-regressive rollout: predict each future day in sequence, feeding
    each prediction back as the newest observation in the look-back window.

    Returns the cumulative predicted spend over `days_to_project` days.
    This gives a model-driven estimate of total spend for the remaining
    budget period — far more accurate than the linear burn-rate approach.
    """
    n = min(max(0, days_to_project), _MAX_PROJECTION_DAYS)
    if n == 0:
        return 0.0

    window_scaled = (
        active_scaler.transform(last_window_raw.reshape(-1, 1))
        .reshape(-1)
        .copy()
    )
    cumulative = 0.0

    for _ in range(n):
        x_in = window_scaled.reshape(1, look_back, 1)
        pred_scaled = float(active_model.predict(x_in, verbose=0).reshape(-1)[0])
        pred_amount = float(
            active_scaler.inverse_transform([[pred_scaled]])[0][0]
        )
        pred_amount = max(0.0, pred_amount)
        cumulative += pred_amount
        # Slide window: drop oldest, append newest predicted value
        window_scaled = np.append(window_scaled[1:], pred_scaled)

    return cumulative


# ---------------------------------------------------------------------------
# Budget-aware risk calibration
# ---------------------------------------------------------------------------

def _compute_budget_aware_risk(
    raw_risk_prob: float,
    predicted_amount: float,
    budget_remaining: float,
    days_left: int,
    risk_threshold: float,
) -> tuple[float, str]:
    """
    Calibrate the XGBoost anomaly probability with the user's actual budget state.

    Blend formula
    ─────────────
      blended_risk = 0.4 × ML_anomaly_prob + 0.6 × budget_pressure

    where  budget_pressure = predicted_amount / safe_daily_limit
           safe_daily_limit = budget_remaining / days_left

    The 60 % weight on budget pressure ensures that a user who is genuinely
    running out of budget always receives a HIGH/MODERATE alert, even when
    their spending is not statistically unusual relative to history.

    Risk-level thresholds
    ─────────────────────
    HIGH     → predicted > total remaining  OR  budget_pressure ≥ 0.90
    MODERATE → blended_risk > risk_threshold  OR  predicted > safe daily limit
    LOW      → everything else
    """
    days_left = max(1, days_left)
    safe_daily_limit = max(1.0, budget_remaining / days_left)
    budget_pressure = float(np.clip(predicted_amount / safe_daily_limit, 0.0, 1.0))

    blended = float(
        np.clip(0.4 * raw_risk_prob + 0.6 * budget_pressure, 0.0, 1.0)
    )

    is_over_total   = predicted_amount > budget_remaining
    is_over_daily   = predicted_amount > safe_daily_limit

    if is_over_total or budget_pressure >= 0.90:
        risk_level = "HIGH"
    elif blended > risk_threshold or is_over_daily:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    return blended, risk_level


# ---------------------------------------------------------------------------
# Public inference entry-point
# ---------------------------------------------------------------------------

def predict_next_day(
    user_id: str,
    category: str,
    budget_remaining: float,
    look_back: int = 30,
    days_left: int = 30,
):
    """
    Predict tomorrow's spend and overspend risk for a user+category pair.

    Personalization pipeline (3-tier adaptive)
    ──────────────────────────────────────────
    Tier 1 (all users):
        • Build user-specific daily spend series from transactions.csv.
        • Use global LSTM + global scaler for LSTM forward pass.
        • Apply budget-aware blended risk calibration.
        • Run multi-step autoregressive projection for remaining period.

    Tier 2 (≥45 days of user data):
        • Fit a user-specific MinMaxScaler on the user's own history.
        • Fine-tune the LSTM via transfer learning:
            – First LSTM layer frozen  (general temporal knowledge)
            – Second LSTM + Dense trainable  (user-specific adaptation)
        • All downstream steps use the personalized model + scaler.

    Parameters
    ──────────
    user_id          : unique user identifier (matched against transactions.csv)
    category         : expense category (must have a trained model)
    budget_remaining : Rs amount still available in the budget goal
    look_back        : sequence window length (should match training value)
    days_left        : calendar days remaining in the budget period

    Returns  (8-tuple)
    ──────────────────
    predicted_amount      – tomorrow's expected spend (Rs)
    risk_prob             – blended risk probability [0, 1]
    risk_level            – "HIGH" | "MODERATE" | "LOW"
    next_day_date         – date object for the predicted day
    day_of_week_str       – e.g. "Monday"
    day_of_week_id        – 0 = Monday … 6 = Sunday
    rolling_7_day_avg     – 7-day rolling mean (reference signal)
    projected_period_spend – cumulative ML forecast for the remaining days
    """
    # ── Load global artifacts ───────────────────────────────────────────────
    paths = _resolve_model_paths(category)
    lstm_model    = tf.keras.models.load_model(paths["model_path_lstm"])
    xgb_model     = joblib.load(paths["model_path_xgb"])
    global_scaler = joblib.load(paths["scaler_path"])
    metadata      = (
        joblib.load(paths["meta_path"])
        if os.path.exists(paths["meta_path"])
        else {}
    )

    effective_look_back   = int(metadata.get("look_back", look_back))
    fallback_amount       = float(metadata.get("fallback_amount", 0.0))
    lstm_quality          = float(metadata.get("lstm_quality", 0.5))
    risk_threshold        = float(metadata.get("risk_threshold", 0.6))
    xgb_feature_columns   = metadata.get(
        "xgb_feature_columns",
        [
            "day_of_week", "day_of_month", "is_weekend",
            "lag_1_amount", "lag_2_amount", "lag_3_amount",
            "rolling_3_mean", "rolling_7_mean", "rolling_14_mean",
            "rolling_7_std", "rolling_14_std", "trend_7",
            "lstm_predicted",
        ],
    )

    df = pd.read_csv(os.path.join(AI_DIR, "transactions.csv"))
    df["date"]   = pd.to_datetime(df["date"], format='mixed', utc=True).dt.date
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["category"] = df["category"].astype(str).str.strip().str.title()
    df.dropna(subset=["amount"], inplace=True)

    user_series = _build_category_series_for_user(df, user_id, category)

    # ── Fallback: no data at all ────────────────────────────────────────────
    if user_series.empty:
        from datetime import date as _date
        today = _date.today()
        next_day_date = today + timedelta(days=1)
        return (
            0.0, 0.0, "LOW",
            next_day_date, next_day_date.strftime("%A"), next_day_date.weekday(),
            0.0, 0.0,
        )

    series_values  = user_series.to_numpy().astype(float)
    n_user_points  = len(series_values)

    # ── Tier selection ──────────────────────────────────────────────────────
    if n_user_points >= _MIN_DAYS_FOR_FINETUNE:
        # Tier 2: personalized scaler + fine-tuned LSTM
        active_scaler = _fit_user_scaler(series_values)
        active_lstm   = _fine_tune_lstm_for_user(
            lstm_model, series_values, active_scaler, effective_look_back
        )
    else:
        # Tier 1: global scaler + global LSTM
        active_scaler = global_scaler
        active_lstm   = lstm_model

    # ── Build look-back window ──────────────────────────────────────────────
    if n_user_points < effective_look_back:
        pad          = np.zeros(effective_look_back - n_user_points, dtype=float)
        last_window  = np.concatenate([pad, series_values])
    else:
        last_window  = series_values[-effective_look_back:]

    scaled_window = active_scaler.transform(last_window.reshape(-1, 1)).reshape(-1)
    X_live        = scaled_window.reshape(1, effective_look_back, 1)

    pred_scaled         = active_lstm.predict(X_live, verbose=0).reshape(-1)
    predicted_amount_raw = float(
        active_scaler.inverse_transform(pred_scaled.reshape(-1, 1)).reshape(-1)[0]
    )

    # ── Determine prediction date ───────────────────────────────────────────
    last_date     = pd.to_datetime(user_series.index.max())
    next_day_date = last_date + timedelta(days=1)

    # ── Compute rolling / lag features (user-specific) ─────────────────────
    def _safe_mean(arr, n):
        return float(np.mean(arr[-n:])) if len(arr) >= n else float(np.mean(arr))

    def _safe_std(arr, n):
        return float(np.std(arr[-n:], ddof=1)) if len(arr) >= n else 0.0

    lag_1 = float(series_values[-1]) if n_user_points >= 1 else 0.0
    lag_2 = float(series_values[-2]) if n_user_points >= 2 else lag_1
    lag_3 = float(series_values[-3]) if n_user_points >= 3 else lag_2
    lag_7 = float(series_values[-7]) if n_user_points >= 7 else lag_1

    rolling_3_mean  = _safe_mean(series_values, 3)
    rolling_7_mean  = _safe_mean(series_values, 7)
    rolling_14_mean = _safe_mean(series_values, 14)
    rolling_7_std   = _safe_std(series_values, 7)
    rolling_14_std  = _safe_std(series_values, 14)
    trend_7         = lag_1 - (float(series_values[-8]) if n_user_points >= 8 else lag_1)

    # New discriminative features
    spend_velocity     = lag_1 - rolling_7_mean
    spend_to_avg_ratio = lag_1 / max(1e-6, rolling_14_mean)
    month_progress     = next_day_date.day / 30.0
    
    sin_day_of_week = np.sin(2 * np.pi * next_day_date.weekday() / 7.0)
    cos_day_of_week = np.cos(2 * np.pi * next_day_date.weekday() / 7.0)
    days_from_payday = min(next_day_date.day - 1, 30 - next_day_date.day)

    # ── Blend LSTM with rolling-mean fallback ───────────────────────────────
    fallback_from_history = rolling_7_mean if rolling_7_mean > 0 else fallback_amount
    blend_weight          = max(0.0, min(1.0, lstm_quality))
    predicted_amount      = max(
        0.0,
        blend_weight * predicted_amount_raw
        + (1.0 - blend_weight) * fallback_from_history,
    )

    # ── Build XGBoost feature vector ────────────────────────────────────────
    live_feature_dict = {
        "day_of_week":        next_day_date.weekday(),
        "sin_day_of_week":    sin_day_of_week,
        "cos_day_of_week":    cos_day_of_week,
        "day_of_month":       next_day_date.day,
        "days_from_payday":   days_from_payday,
        "month_progress":     month_progress,
        "is_weekend":         int(next_day_date.weekday() >= 5),
        "lag_1_amount":       lag_1,
        "lag_2_amount":       lag_2,
        "lag_3_amount":       lag_3,
        "lag_7_amount":       lag_7,
        "rolling_3_mean":     rolling_3_mean,
        "rolling_7_mean":     rolling_7_mean,
        "rolling_14_mean":    rolling_14_mean,
        "rolling_7_std":      rolling_7_std,
        "rolling_14_std":     rolling_14_std,
        "trend_7":            trend_7,
        "spend_velocity":     spend_velocity,
        "spend_to_avg_ratio": spend_to_avg_ratio,
        "lstm_predicted":     predicted_amount,
    }

    live_features = pd.DataFrame([live_feature_dict])
    # reindex to exactly the columns the trained XGB expects (backward-safe)
    live_features = live_features.reindex(columns=xgb_feature_columns, fill_value=0.0)
    live_features.fillna(0.0, inplace=True)

    raw_risk_prob = float(xgb_model.predict_proba(live_features)[0][1])

    # ── Budget-aware blended risk calibration ───────────────────────────────
    blended_risk_prob, risk_level = _compute_budget_aware_risk(
        raw_risk_prob    = raw_risk_prob,
        predicted_amount = predicted_amount,
        budget_remaining = budget_remaining,
        days_left        = days_left,
        risk_threshold   = risk_threshold,
    )

    # ── Multi-step cumulative period projection ─────────────────────────────
    projected_period_spend = _project_cumulative_spend(
        active_model    = active_lstm,
        active_scaler   = active_scaler,
        last_window_raw = last_window,
        look_back       = effective_look_back,
        days_to_project = days_left,
    )

    return (
        predicted_amount,
        blended_risk_prob,
        risk_level,
        next_day_date,
        next_day_date.strftime("%A"),
        next_day_date.weekday(),
        rolling_7_mean,
        projected_period_spend,
    )
