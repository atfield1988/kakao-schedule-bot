"""
PythonAnywhere WSGI 설정

이 파일은 PythonAnywhere Web 탭의 WSGI 설정 파일에서 참조됩니다.
로컬 개발에서는 사용하지 않습니다.
"""

import sys
import os

# 프로젝트 경로 추가
# PythonAnywhere: /home/yourusername/kakao-schedule-bot
path = '/home/yourusername/kakao-schedule-bot'
if path not in sys.path:
    sys.path.insert(0, path)

# 환경 변수 설정 (WSGI 파일에서 직접 설정하는 것이 더 안전)
# .env 파일 대신 여기서 설정
os.environ['DB_HOST'] = 'yourusername.mysql.pythonanywhere-services.com'
os.environ['DB_PORT'] = '3306'
os.environ['DB_USER'] = 'yourusername'
os.environ['DB_PASSWORD'] = 'your_mysql_password'
os.environ['DB_NAME'] = 'yourusername$scheduledb'
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['FLASK_ENV'] = 'production'

# Flask 앱 임포트
from app import app as application

# PythonAnywhere는 'application' 이름을 찾습니다
