"""Flask 앱 설정"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """기본 설정 클래스"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'scheduledb')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = (FLASK_ENV == 'development')
    
    @staticmethod
    def init_app(app):
        """앱 초기화 시 실행되는 설정"""
        pass


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False


# 환경별 설정 매핑
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
