import re
from flask import render_template, Blueprint, flash, redirect, url_for, request, current_app, jsonify
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
    return render_template('status.html', title='Status')


@main_bp.route('/api/weight-data')
def weight_data():
    user = get_or_create_default_user()
    period = request.args.get('period', '30') # 30 dagar som standard

    if period == 'all':
        start_date = None
    else:
        try:
            days = int(period)
            start_date = date.today() - timedelta(days=days-1)
        except ValueError:
            return jsonify({'error': 'Invalid period format'}), 400

    query = db.select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.date.asc())
    if start_date:
        query = query.where(WeightLog.date >= start_date)
    
    logs = db.session.scalars(query).all()

    labels = [log.date.strftime('%Y-%m-%d') for log in logs]
    data = [log.weight for log in logs]

    return jsonify(labels=labels, data=data)


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
    """Tar emot data från sökresultat, skalar näringsvärden och loggar i databasen."""
    try:
        food_name = request.form.get('food_name')
        food_description = request.form.get('food_description')
        meal_type = request.form.get('meal_type')
        grams = int(request.form.get('grams', 100))

        # Extrahera näringsvärden per 100g
        base_calories_match = re.search(r"Calories: ([\d.]+)kcal", food_description)
        base_fat_match = re.search(r"Fat: ([\d.]+)g", food_description)
        base_carbs_match = re.search(r"Carbs: ([\d.]+)g", food_description)
        base_protein_match = re.search(r"Protein: ([\d.]+)g", food_description)

        if not all([food_name, meal_type, base_calories_match]):
            flash('Något gick fel, all data kunde inte läsas in.', 'danger')
            return redirect(url_for('main.diet'))

        # Hämta värden per 100g
        cals_per_100g = float(base_calories_match.group(1))
        fat_per_100g = float(base_fat_match.group(1)) if base_fat_match else 0
        carbs_per_100g = float(base_carbs_match.group(1)) if base_carbs_match else 0
        protein_per_100g = float(base_protein_match.group(1)) if base_protein_match else 0
        
        # Skala värden baserat på angivna gram
        scaling_factor = grams / 100.0
        
        user = get_or_create_default_user()
        new_log = FoodLog(
            user_id=user.id,
            food_name=food_name,
            meal_type=meal_type,
            grams=grams,
            calories=cals_per_100g * scaling_factor,
            fat=fat_per_100g * scaling_factor,
            carbohydrates=carbs_per_100g * scaling_factor,
            protein=protein_per_100g * scaling_factor,
            base_servings_info=food_description,
            date=date.today()
        )

        db.session.add(new_log)
        db.session.commit()
        flash(f"{food_name} ({grams}g) har lagts till i {meal_type}!", 'success')
    
    except (ValueError, TypeError):
        flash("Felaktig inmatning. Ange ett giltigt antal gram.", 'danger')

    return redirect(url_for('main.diet'))

@main_bp.route('/diet/delete/<int:log_id>', methods=['POST'])
def delete_food_log(log_id):
    """Tar bort en specifik matlogg."""
    log_to_delete = db.session.get(FoodLog, log_id)
    if log_to_delete:
        db.session.delete(log_to_delete)
        db.session.commit()
        flash("Matvaran har tagits bort.", "success")
    else:
        flash("Kunde inte hitta loggen att ta bort.", "warning")
    return redirect(url_for('main.diet'))
