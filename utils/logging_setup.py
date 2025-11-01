"""
로그 로테이션 및 레벨 설정

이 모듈은 Flask 앱의 로깅을 설정하며,
개발/프로덕션 환경에 따라 자동으로 로그 레벨을 전환합니다.
"""

import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(app):
    """
    Flask 앱 로깅 설정
    
    Args:
        app (Flask): Flask 앱 객체
    
    Note:
        - 개발 환경 (FLASK_ENV=development): DEBUG 레벨
        - 프로덕션 환경 (그 외): INFO 레벨
        - 로그 로테이션: 10MB × 5개 백업
        - 에러 로그: logs/error.log
        - 감사 로그: INFO 레벨 (신청/취소 기록)
    
    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> setup_logging(app)
        >>> app.logger.info("User 123 applied")  # INFO 레벨 기록
    """
    # 로그 디렉토리 생성
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # 환경 변수로 로그 레벨 자동 전환
    if os.environ.get('FLASK_ENV') == 'development':
        log_level = logging.DEBUG
        app.logger.info("🔧 Development mode: DEBUG logging enabled")
    else:
        log_level = logging.INFO
        app.logger.info("🚀 Production mode: INFO logging enabled")
    
    # RotatingFileHandler 설정
    # 10MB 초과 시 자동으로 error.log.1, error.log.2... 생성
    file_handler = RotatingFileHandler(
        'logs/error.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,              # 최대 5개 백업 파일
        encoding='utf-8'
    )
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Flask 앱 로거에 핸들러 추가
    app.logger.addHandler(file_handler)
    app.logger.setLevel(log_level)
    
    # 시작 메시지
    app.logger.info('=' * 50)
    app.logger.info('Schedule Bot Starting')
    app.logger.info(f'Log level: {logging.getLevelName(log_level)}')
    app.logger.info(f'Log file: logs/error.log')
    app.logger.info('=' * 50)


def log_api_call(app, endpoint, user_id, params=None):
    """
    API 호출 로그 기록 (감사 로그)
    
    Args:
        app (Flask): Flask 앱 객체
        endpoint (str): API 엔드포인트 (예: "/apply")
        user_id (str): 사용자 ID
        params (dict, optional): 추가 파라미터
    
    Example:
        >>> log_api_call(app, "/apply", "user123", {"schedule_id": 50})
        # 로그: INFO - API Call: /apply | User: user123 | Params: {...}
    """
    log_msg = f"API Call: {endpoint} | User: {user_id}"
    if params:
        log_msg += f" | Params: {params}"
    app.logger.info(log_msg)


def log_admin_action(app, action, admin_id, details=None):
    """
    관리자 액션 로그 기록
    
    Args:
        app (Flask): Flask 앱 객체
        action (str): 액션 종류 (예: "DELETE_SCHEDULE")
        admin_id (str): 관리자 ID
        details (dict, optional): 상세 정보
    
    Example:
        >>> log_admin_action(app, "DELETE_SCHEDULE", "admin123", {"schedule_id": 50})
        # 로그: INFO - Admin Action: DELETE_SCHEDULE | Admin: admin123 | Details: {...}
    """
    log_msg = f"Admin Action: {action} | Admin: {admin_id}"
    if details:
        log_msg += f" | Details: {details}"
    app.logger.info(log_msg)
