import requests
from flask import current_app

def get_fatsecret_token():
    """Hämtar en Oauth 2.0 access token från FatSecret API."""
    client_id = current_app.config['FATSECRET_CLIENT_ID']
    client_secret = current_app.config['FATSECRET_CLIENT_SECRET']
    
    if not client_id or not client_secret:
        current_app.logger.error("FatSecret client ID eller secret är inte konfigurerad.")
        return None

    token_url = 'https://oauth.fatsecret.com/connect/token'
    payload = {
        'grant_type': 'client_credentials',
        'scope': 'basic'
    }
    
    try:
        response = requests.post(token_url, data=payload, auth=(client_id, client_secret), timeout=10)
        response.raise_for_status()  # Kasta ett undantag för 4xx/5xx-svar
        return response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Kunde inte hämta FatSecret-token: {e}")
        return None

def search_food(search_term, token):
    """Söker efter matvaror med FatSecret API."""
    if not token:
        return None

    search_url = 'https://platform.fatsecret.com/rest/server.api'
    params = {
        'method': 'foods.search',
        'search_expression': search_term,
        'format': 'json',
        'max_results': 20
    }
    headers = {
        'Authorization': f'Bearer {token}'
    }

    try:
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Kunde inte söka efter mat: {e}")
        return None 