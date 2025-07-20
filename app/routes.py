from flask import render_template, Blueprint

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', title='Dashboard')
