import os
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv
import hashlib

load_dotenv()

class FyersAuth:
    def __init__(self):
        self.client_id = os.getenv('FYERS_CLIENT_ID')
        self.secret_key = os.getenv('FYERS_SECRET_KEY')
        self.redirect_uri = os.getenv('FYERS_REDIRECT_URI', 'https://trade.fyers.in/api-login/redirect-uri/index.html')
        self.pin = os.getenv('FYERS_PIN')
        self.access_token = None
        self.fyers = None
    
    def generate_auth_code_url(self):
        """Generate URL for manual authentication (initial setup)"""
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type='code',
            grant_type='authorization_code'
        )
        return session.generate_authcode()
    
    def generate_access_token(self, auth_code):
        """Generate access token from auth code"""
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type='code',
            grant_type='authorization_code'
        )
        session.set_token(auth_code)
        response = session.generate_token()
        
        if 'access_token' in response:
            self.access_token = response['access_token']
            # Save to file for persistence
            with open('fyers_access_token.txt', 'w') as f:
                f.write(self.access_token)
            return True
        return False
    
    def load_access_token(self):
        """Load saved access token"""
        try:
            with open('fyers_access_token.txt', 'r') as f:
                self.access_token = f.read().strip()
            return True
        except FileNotFoundError:
            return False
    
    def get_fyers_client(self):
        """Get authenticated Fyers client"""
        if not self.access_token:
            if not self.load_access_token():
                return None
        
        self.fyers = fyersModel.FyersModel(
            client_id=self.client_id,
            token=self.access_token,
            log_path=''
        )
        return self.fyers
    
    def test_connection(self):
        """Test if auth is working"""
        fyers = self.get_fyers_client()
        if not fyers:
            return False
        
        try:
            # Try to get profile
            response = fyers.get_profile()
            return response.get('code') == 200
        except:
            return False
