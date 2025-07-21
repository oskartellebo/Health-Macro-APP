import re
from flask import render_template, Blueprint, flash, redirect, url_for, request, current_app
from app import db
from app.models import User, WeightLog, FoodLog, StepLog, CardioLog, FightRondLog
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
    """Hämtar eller skapar en standardanvändare för att säkerställa att appen fungerar."""
    # Försök hämta användare med id 1
    user = db.session.get(User, 1)
    if user is None:
        # Om användaren inte finns, skapa den
        user = User(id=1, username='default')
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Logga felet om det uppstår problem med att skapa användaren
            current_app.logger.error(f"Kunde inte skapa standardanvändare: {e}")
            raise
    return user


# --- Routes ---
@main_bp.route('/')
@main_bp.route('/dashboard')
def dashboard():
    """Renderar dashboard-sidan."""
    user = get_or_create_default_user()
    weight_stats = stats_service.calculate_weight_stats(user.id)
    calorie_stats = stats_service.calculate_calorie_stats(user.id)
    
    # Hämta data för grafen
    logs_query = db.select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.date.asc())
    logs = db.session.scalars(logs_query).all()
    
    labels = [log.date.strftime('%Y-%m-%d') for log in logs]
    data = [log.weight for log in logs]

    return render_template(
        'dashboard.html', 
        title='Dashboard', 
        weight_stats=weight_stats,
        calorie_stats=calorie_stats,
        labels=labels, 
        data=data
    )

@main_bp.route('/weight', methods=['GET', 'POST'])
def weight():
    form = WeightForm()
    user = get_or_create_default_user()

    if form.validate_on_submit():
        # Kontrollera om en logg för detta datum redan finns
        existing_log = db.session.scalar(
            db.select(WeightLog).where(
                WeightLog.user_id == user.id,
                WeightLog.date == form.date.data
            )
        )
        if existing_log:
            existing_log.weight = form.weight.data
            flash('Vikten för det valda datumet har uppdaterats!', 'success')
        else:
            new_log = WeightLog(weight=form.weight.data, date=form.date.data, user_id=user.id)
            db.session.add(new_log)
            flash('Ny vikt har loggats!', 'success')
        
        db.session.commit()
        return redirect(url_for('main.weight'))

    # Hämta befintliga loggar
    logs_query = db.select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.date.desc())
    logs = db.session.scalars(logs_query).all()
    stats = stats_service.calculate_weight_stats(user.id)
    
    return render_template('weight.html', title='Vikt', form=form, weight_logs=logs, stats=stats)


@main_bp.route('/training', methods=['GET', 'POST'])
def training():
    """Renderar träningssidan och hanterar loggning av aktivitet."""
    user = get_or_create_default_user()

    if request.method == 'POST':
        if 'log_steps' in request.form:
            try:
                steps = int(request.form.get('steps'))
                # Sök efter befintlig logg för dagen
                log = db.session.scalar(db.select(StepLog).where(StepLog.user_id==user.id, StepLog.date==date.today()))
                if log:
                    log.steps = steps # Uppdatera
                else:
                    log = StepLog(steps=steps, user_id=user.id) # Skapa ny
                    db.session.add(log)
                db.session.commit()
                flash(f"Loggade {steps} steg!", "success")
            except (ValueError, TypeError):
                flash("Vänligen ange ett giltigt antal steg.", "danger")
        
        elif 'log_cardio' in request.form:
            try:
                avg_bpm = int(request.form.get('avg_bpm'))
                duration = int(request.form.get('duration_minutes'))
                calories_burned = int(avg_bpm * duration * 0.08)
                
                log = CardioLog(
                    avg_bpm=avg_bpm, 
                    duration_minutes=duration, 
                    calories_burned=calories_burned, 
                    user_id=user.id
                )
                db.session.add(log)
                db.session.commit()
                flash(f"Loggade konditionspass! ({calories_burned} kcal)", "success")
            except (ValueError, TypeError):
                flash("Vänligen fyll i både puls och tid.", "danger")

        elif 'log_fight_rond' in request.form:
            try:
                bpm = int(request.form.get('bpm'))
                # Kalorier för en 3-minuters rond
                calories_burned = int(bpm * 3 * 0.08)
                log = FightRondLog(bpm=bpm, calories_burned=calories_burned, user_id=user.id)
                db.session.add(log)
                db.session.commit()
                flash(f"Loggade fight-rond med {bpm} BPM! ({calories_burned} kcal)", "success")
            except (ValueError, TypeError):
                flash("Vänligen ange en giltig puls.", "danger")

        return redirect(url_for('main.training'))
    
    # Hämta dagens loggar för att visa på sidan
    today = date.today()
    step_log = db.session.scalar(db.select(StepLog).where(StepLog.user_id==user.id, StepLog.date==today))
    cardio_logs = db.session.scalars(db.select(CardioLog).where(CardioLog.user_id==user.id, CardioLog.date==today)).all()
    fight_rond_logs = db.session.scalars(db.select(FightRondLog).where(FightRondLog.user_id==user.id, FightRondLog.date==today)).all()
        
    return render_template('training.html', title='Träning', step_log=step_log, cardio_logs=cardio_logs, fight_rond_logs=fight_rond_logs)


@main_bp.route('/status')
def status():
    """Renderar statussidan med sammanfattad data."""
    # TODO: Hämta och bearbeta data för alla sektioner
    return render_template('status.html', title='Status')


@main_bp.route('/diet', methods=['GET', 'POST'])
def diet():
    """Renderar sidan för kostloggning och hanterar sökning."""
    search_results = None
    if request.method == 'POST' and 'search_ingredient' in request.form:
        search_term = request.form.get('search_ingredient')
        print(f"--- SÖKER EFTER: '{search_term}' ---")

        if search_term:
            token = fatsecret_service.get_fatsecret_token()
            if token:
                print("--- TOKEN MOTTAGEN ---")
                search_data = fatsecret_service.search_food(search_term, token)
                print(f"--- API-SVAR: {search_data} ---")

                if search_data and 'foods' in search_data and 'food' in search_data['foods']:
                    search_results = search_data['foods']['food']
                else:
                    flash('Inga resultat hittades för den söktermen.', 'info')
                    if search_data and 'error' in search_data:
                        error_message = search_data['error'].get('message', 'Okänt fel från API.')
                        flash(f"API-fel: {error_message}", 'danger')
            else:
                print("--- FEL: KUNDE INTE HÄMTA TOKEN ---")
                flash('Kunde inte ansluta till FatSecret. Kontrollera API-nycklarna.', 'danger')

    # Hämta dagens loggade mat
    user = get_or_create_default_user()
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

    user = get_or_create_default_user()

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
