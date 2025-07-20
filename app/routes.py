from flask import render_template, Blueprint, flash, redirect, url_for
from app import db
from app.models import User, WeightLog
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


# --- Routes ---
@main_bp.route('/')
@main_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', title='Dashboard')

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
        return redirect(url_for('main.weight'))

    # Hämta data för rendering
    logs_query = db.select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.date.desc())
    logs = db.session.scalars(logs_query).all()
    stats = calculate_weight_stats(user.id)
    
    return render_template('weight.html', title='Vikt', form=form, logs=logs, stats=stats)
