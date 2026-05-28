from app.crud.budget import get_budgets_by_user
from app.crud.daily_prediction import create_daily_prediction
from ai.budget_prediction_model.inference import predict_next_day
from app.models.user import User
from app.schemas.ai_predictions import DailyPredictionCreate
from decimal import Decimal
import logging
from app.utils import dispatcher
from app.utils.events import PredictionGenerated


def generate_and_store_predictions_for_user(
    db, user_id: str, time_horizon: str = "30d"
):
    """
    Generate and store predictions for all budgets of a user for a given time horizon. Idempotent: skips if already exists for today and horizon.
    """
    budgets = get_budgets_by_user(db, user_id=user_id)
    if not budgets:
        return
    from app.models.daily_prediction import DailyPrediction

    # Map time_horizon to look_back days for inference.
    # Monthly horizons are fixed to 4 weeks.
    look_back_map = {"7d": 7, "30d": 28, "90d": 90, "calendar_month": 28}
    look_back = look_back_map.get(time_horizon, 28)

    for budget in budgets:
        try:
            (
                predicted_amount,
                risk_prob,
                risk_level,
                prediction_date,
                day_of_week,
                day_of_week_id,
                rolling_7_day_avg,
            ) = predict_next_day(
                user_id=user_id,
                category=budget.category,
                budget_remaining=budget.remaining_budget,
                look_back=look_back,
            )

            # Check if user was already warned today for this category/horizon
            existing_today_pred = db.query(DailyPrediction).filter_by(
                user_id=user_id,
                category=budget.category,
                prediction_date=prediction_date,
                time_horizon=time_horizon,
            ).first()
            already_notified = existing_today_pred is not None and existing_today_pred.risk_level == "HIGH"

            # Delete existing prediction for this user/category/date/horizon (if any)
            db.query(DailyPrediction).filter_by(
                user_id=user_id,
                category=budget.category,
                prediction_date=prediction_date,
                time_horizon=time_horizon,
            ).delete()
            db.commit()

            prediction_to_store = DailyPredictionCreate(
                user_id=user_id,
                prediction_date=prediction_date,
                category=budget.category,
                day_of_week=day_of_week,
                day_of_week_id=day_of_week_id,
                rolling_7_day_avg=Decimal(float(rolling_7_day_avg)),
                budget_remaining=Decimal(budget.remaining_budget),
                predicted_amount=Decimal(float(predicted_amount)),
                risk_probability=Decimal(float(risk_prob)),
                risk_level=risk_level,
                time_horizon=time_horizon,
            )
            pred = create_daily_prediction(db, prediction=prediction_to_store)
            payload = prediction_to_store.dict()
            payload["prediction_id"] = getattr(pred, "id", None)
            dispatcher.dispatch(
                PredictionGenerated(db, user_id, payload["prediction_id"], payload)
            )

            # Trigger real-time overspending email if risk shifts to HIGH and user hasn't been warned today
            if (risk_level == "HIGH" or float(risk_prob) > 0.7) and not already_notified:
                user_model = db.query(User).filter(User.user_id == user_id).first()
                if user_model and user_model.email:
                    from app.utils.email import send_budget_warning_email
                    send_budget_warning_email(
                        to_email=user_model.email,
                        category=budget.category,
                        remaining_budget=float(budget.remaining_budget),
                        predicted_amount=float(predicted_amount),
                        risk_probability=float(risk_prob),
                    )
        except FileNotFoundError:
            continue
        except Exception as e:
            logging.error(f"Error predicting for category {budget.category}: {e}")
            continue
