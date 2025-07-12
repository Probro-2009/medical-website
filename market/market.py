from flask import Blueprint, render_template

market_bp = Blueprint('market', __name__, template_folder='templates', static_folder='static')

@market_bp.route('/market')
def market_home():
    return render_template('market.html')
