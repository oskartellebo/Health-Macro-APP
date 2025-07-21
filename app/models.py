from app import db
from datetime import date

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    weight_logs = db.relationship('WeightLog', backref='author', lazy='dynamic')
    
    def __init__(self, id=None, username=None):
        if id is not None:
            self.id = id
        if username is not None:
            self.username = username

    def __repr__(self):
        return f'<User {self.username}>'

class WeightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    weight = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<WeightLog {self.date}: {self.weight}kg>'

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    meal_type = db.Column(db.String(50), nullable=False)  # t.ex. 'Frukost', 'Lunch'
    food_name = db.Column(db.String(100), nullable=False)
    grams = db.Column(db.Integer, nullable=False, default=100)
    calories = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, nullable=True)
    carbohydrates = db.Column(db.Float, nullable=True)
    fat = db.Column(db.Float, nullable=True)
    base_servings_info = db.Column(db.String(200), nullable=True) # Sparar originalbeskrivning, t.ex. "Per 100g"
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<FoodLog {self.date} - {self.meal_type}: {self.food_name} ({self.grams}g)>'

class StepLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    steps = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<StepLog {self.date}: {self.steps} steg>'

class CardioLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    duration_seconds = db.Column(db.Integer, nullable=False) # Ändrat från minuter till sekunder
    avg_bpm = db.Column(db.Integer, nullable=False)
    calories_burned = db.Column(db.Integer, nullable=False)
    distance_km = db.Column(db.Float, nullable=True) # Ny kolumn för distans
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<CardioLog {self.date}: {self.duration_seconds} sek, {self.calories_burned} kcal>'

class FightRondLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    bpm = db.Column(db.Integer, nullable=False)
    calories_burned = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<FightRondLog {self.date}: {self.bpm} BPM>'
