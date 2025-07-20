import re
from flask import render_template, Blueprint, flash, redirect, url_for, request
from app import db
from app.models import User, WeightLog, FoodLog
from app.services import stats_service
from app.services import fatsecret_service
from flask_wtf import FlaskForm
from wtforms import FloatField, DateField, SubmitField
from wtforms.validators import DataRequired
from datetime import date, timedelta

main_bp = Blueprint('main', __name__)

# --- Formulär ---
class WeightForm(FlaskForm):
    weight = FloatField('Vikt (kg)', validators=[DataRequired()])
    date = DateField('Datum', default=date.today, validators=[DataRequired()])
    submit = SubmitField('Spara Vikt')

# --- Helper-funktioner ---
def get_or_create_default_user():
    """Hämtar eller skapar en standardanvändare för testning."""
    user = db.session.scalar(db.select(User).where(User.username == 'default'))
    if not user:
        user = User(username='default')
        db.session.add(user)
        db.session.commit()
    return user


# --- Routes ---
@main_bp.route('/')
@main_bp.route('/dashboard')
def dashboard():
    user = get_or_create_default_user()
    
    # Hämta senaste vikt
    latest_log_query = db.select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.date.desc())
    latest_log = db.session.scalars(latest_log_query).first()
    
    # Hämta statistik från tjänstelagret
    stats = stats_service.calculate_weight_stats(user.id)
    
    # Hämta data för graf (senaste 30 dagarna)
    thirty_days_ago = date.today() - timedelta(days=29)
    chart_data_query = db.select(WeightLog).where(
        WeightLog.user_id == user.id,
        WeightLog.date >= thirty_days_ago
    ).order_by(WeightLog.date.asc())
    chart_logs = db.session.scalars(chart_data_query).all()

    # Formatera data för Chart.js
    chart_labels = [log.date.strftime('%b %d') for log in chart_logs]
    chart_values = [log.weight for log in chart_logs]

    return render_template('dashboard.html', 
                           title='Dashboard', 
                           latest_log=latest_log, 
                           stats=stats,
                           chart_labels=chart_labels,
                           chart_values=chart_values)

@main_bp.route('/weight', methods=['GET', 'POST'])
def weight():
    form = WeightForm()
    user = get_or_create_default_user()

    if form.validate_on_submit():
        # Kontrollera om en logg för detta datum redan finns
        existing_log_query = db.select(WeightLog).where(
            WeightLog.user_id == user.id,
            WeightLog.date == form.date.data
        )
        existing_log = db.session.scalar(existing_log_query)
        if existing_log:
            existing_log.weight = form.weight.data
            flash('Vikten för det valda datumet har uppdaterats!', 'success')
        else:
            # Parametrarna matchar nu kolumnnamnen i WeightLog-modellen
            new_log = WeightLog(weight=form.weight.data, date=form.date.data, user_id=user.id)
            db.session.add(new_log)
            flash('Ny vikt har loggats!', 'success')
        
        db.session.commit()
        flash('Vikt loggad!', 'success')
        return redirect(url_for('main.weight'))

    # Hämta befintliga loggar
    logs_query = db.select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.date.desc())
    logs = db.session.scalars(logs_query).all()
    stats = stats_service.calculate_weight_stats(user.id)
    
    return render_template('weight.html', title='Vikt', form=form, weight_logs=logs, stats=stats)


@main_bp.route('/diet', methods=['GET', 'POST'])
def diet():
    """Renderar sidan för kostloggning och hanterar sökning."""
    search_results = None
    if request.method == 'POST' and 'search_ingredient' in request.form:
        search_term = request.form.get('search_ingredient')
        if search_term:
            token = fatsecret_service.get_fatsecret_token()
            if token:
                search_data = fatsecret_service.search_food(search_term, token)
                if search_data and 'foods' in search_data and 'food' in search_data['foods']:
                    search_results = search_data['foods']['food']
                else:
                    flash('Inga resultat hittades för den söktermen.', 'info')
            else:
                flash('Kunde inte ansluta till FatSecret. Kontrollera API-nycklarna.', 'danger')

    # Hämta dagens loggade mat
    user = db.session.scalar(db.select(User).where(User.id == 1)) # Anta användare 1
    today_logs_query = db.select(FoodLog).where(FoodLog.user_id == user.id, FoodLog.date == date.today()).order_by(FoodLog.id)
    today_logs = db.session.scalars(today_logs_query).all()

    # Gruppera efter måltidstyp
    grouped_logs = {}
    for log in today_logs:
        if log.meal_type not in grouped_logs:
            grouped_logs[log.meal_type] = []
        grouped_logs[log.meal_type].append(log)

    return render_template('diet.html', title='Kost', search_results=search_results, food_logs=grouped_logs)


@main_bp.route('/diet/add', methods=['POST'])
def add_food_log():
    """Tar emot data från sökresultat och loggar mat i databasen."""
    food_name = request.form.get('food_name')
    food_description = request.form.get('food_description')
    meal_type = request.form.get('meal_type')

    # Extrahera näringsvärden med regex
    calories = re.search(r"Calories: ([\d.]+)kcal", food_description)
    fat = re.search(r"Fat: ([\d.]+)g", food_description)
    carbs = re.search(r"Carbs: ([\d.]+)g", food_description)
    protein = re.search(r"Protein: ([\d.]+)g", food_description)

    if not all([food_name, meal_type, calories]):
        flash('Något gick fel, all data kunde inte läsas in.', 'danger')
        return redirect(url_for('main.diet'))

    user = db.session.scalar(db.select(User).where(User.id == 1)) # Anta användare 1

    new_log = FoodLog(
        user_id=user.id,
        food_name=food_name,
        meal_type=meal_type,
        calories=float(calories.group(1)),
        fat=float(fat.group(1)) if fat else 0,
        carbohydrates=float(carbs.group(1)) if carbs else 0,
        protein=float(protein.group(1)) if protein else 0,
        date=date.today()
    )

    db.session.add(new_log)
    db.session.commit()
    flash(f"{food_name} har lagts till i {meal_type}!", 'success')
    return redirect(url_for('main.diet'))
