"""
Flask 메인 애플리케이션

카카오톡 스케줄 관리 챗봇의 메인 서버입니다.
"""

from flask import Flask
from config import config
from utils.db import create_connection_pool
from utils.logging_setup import setup_logging
import utils.db as db_module
import os


def create_app(config_name=None):
    """
    Flask 앱 팩토리
    
    Args:
        config_name (str): 설정 이름 ('development' or 'production')
    
    Returns:
        Flask: 설정된 Flask 앱 객체
    """
    app = Flask(__name__)
    
    # 환경 설정 로드
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # 설정 적용
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 로깅 설정
    setup_logging(app)
    
    # Connection Pool 초기화
    try:
        db_module.connection_pool = create_connection_pool()
        app.logger.info("✅ MySQL Connection Pool initialized")
    except Exception as e:
        app.logger.error(f"❌ Failed to initialize Connection Pool: {e}")
        raise
    
    # 라우트 등록
    from routes import user_routes, admin_routes, web_routes
    
    app.register_blueprint(user_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(web_routes.bp)
    
    app.logger.info("✅ All routes registered")
    
    # 헬스 체크 엔드포인트
    @app.route('/health')
    def health_check():
        """서버 상태 확인"""
        return {
            "status": "healthy",
            "service": "kakao-schedule-bot",
            "version": "1.0.0"
        }, 200
    
    # 에러 핸들러
    @app.errorhandler(Exception)
    def handle_error(e):
        """
        전역 에러 핸들러
        
        모든 예외를 로그에 기록하고 
        사용자에게는 통일된 에러 메시지를 반환합니다.
        """
        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        
        from utils.kakao_response import simple_text
        return simple_text("서버 에러가 발생했습니다. 잠시 후 다시 시도해주세요."), 500
    
    return app


# 앱 인스턴스 생성
app = create_app()


if __name__ == '__main__':
    # 로컬 개발 서버 실행 (개발 전용)
    # 프로덕션에서는 WSGI 서버 사용
    app.run(host='0.0.0.0', port=5000, debug=True)
