from app import db
from datetime import date

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    weight_logs = db.relationship('WeightLog', backref='author', lazy='dynamic')
    
    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return f'<User {self.username}>'

class WeightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, index=True, default=date.today)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Vi tar bort den explicita __init__ då SQLAlchemy hanterar det bra
    # när parametrarna i anropet matchar kolumnnamnen.
    # Detta är ofta renare.

    def __repr__(self):
        return f'<WeightLog {self.date}: {self.weight}kg>'
