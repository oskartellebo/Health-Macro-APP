from datetime import date, timedelta
from app import db
from app.models import User, WeightLog, FoodLog

def calculate_weight_stats(user_id):
    """Beräknar viktstatistik för en given användare."""
    today = date.today()
    
    # Senaste 7 dagarna
    start_of_period1 = today - timedelta(days=6)
    logs_p1_query = db.select(WeightLog.weight).where(
        WeightLog.user_id == user_id,
        WeightLog.date >= start_of_period1
    )
    logs_p1 = db.session.scalars(logs_p1_query).all()
    
    avg_p1 = round(sum(logs_p1) / len(logs_p1), 1) if logs_p1 else None

    # Föregående 7-dagarsperiod
    start_of_period2 = today - timedelta(days=13)
    end_of_period2 = today - timedelta(days=7)
    logs_p2_query = db.select(WeightLog.weight).where(
        WeightLog.user_id == user_id,
        WeightLog.date >= start_of_period2,
        WeightLog.date <= end_of_period2
    )
    logs_p2 = db.session.scalars(logs_p2_query).all()

    avg_p2 = round(sum(logs_p2) / len(logs_p2), 1) if logs_p2 else None
    
    change = None
    if avg_p1 is not None and avg_p2 is not None:
        change = avg_p1 - avg_p2

    return {"avg_7_days": avg_p1, "change": change}

def calculate_calorie_stats(user_id):
    """Beräknar dagens kaloriintag och mål."""
    today = date.today()
    
    # Hämta totala kalorier för idag
    total_calories_query = db.session.query(db.func.sum(FoodLog.calories)).filter(
        FoodLog.user_id == user_id,
        FoodLog.date == today
    )
    total_calories = total_calories_query.scalar() or 0
    
    # Hämta användarens mål (hårdkodat för nu)
    # TODO: Flytta till User-modellen
    calorie_goal = 2200
    
    remaining_calories = calorie_goal - total_calories
    progress_percentage = (total_calories / calorie_goal) * 100 if calorie_goal > 0 else 0
    
    return {
        "total_calories": total_calories,
        "calorie_goal": calorie_goal,
        "remaining_calories": remaining_calories,
        "progress_percentage": progress_percentage
    }
