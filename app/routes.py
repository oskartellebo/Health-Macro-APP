from flask import render_template, Blueprint, flash, redirect, url_for
from app import db
from app.models import User, WeightLog
from app.services import stats_service
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
        return redirect(url_for('main.weight'))

    # Hämta data för rendering
    logs_query = db.select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.date.desc())
    logs = db.session.scalars(logs_query).all()
    stats = stats_service.calculate_weight_stats(user.id)
    
    return render_template('weight.html', title='Vikt', form=form, logs=logs, stats=stats)
