import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'churnprediction-secret-key-2026')
    DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
    
    # Default admin credentials
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'
