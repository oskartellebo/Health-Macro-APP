import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'du-kommer-aldrig-gissa'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # FatSecret API Keys
    FATSECRET_CLIENT_ID = os.environ.get('FATSECRET_CLIENT_ID')
    FATSECRET_CLIENT_SECRET = os.environ.get('FATSECRET_CLIENT_SECRET') 