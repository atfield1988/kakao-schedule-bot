"""
웹페이지 라우트

- 스케줄 현황 (색상 코딩)
- 관리자 에러 대시보드
"""

from flask import Blueprint, render_template, current_app
from utils.db import get_db_connection
from utils.datetime_parser import format_datetime_korean

bp = Blueprint('web', __name__, url_prefix='/web')


@bp.route('/status')
def status_page():
    """
    스케줄 현황 웹페이지 (색상 코딩)
    
    URL: https://yourusername.pythonanywhere.com/web/status
    
    색상 코딩:
        - 마감 (current_count >= capacity): 빨강
        - 미달 (current_count < capacity): 초록
    
    Returns:
        HTML: 스케줄 테이블
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id,
                schedule_datetime,
                duration_minutes,
                capacity,
                current_count,
                created_at
            FROM schedules
            ORDER BY schedule_datetime
        """)
        
        schedules = cursor.fetchall()
        
        # 데이터 가공
        schedule_list = []
        for row in schedules:
            schedule_id, schedule_dt, duration_mins, capacity, current_count, created_at = row
            
            # 색상 클래스 결정
            if current_count >= capacity:
                status_class = 'full'  # 마감
            else:
                status_class = 'available'  # 미달
            
            schedule_list.append({
                'id': schedule_id,
                'datetime': schedule_dt,
                'datetime_korean': format_datetime_korean(schedule_dt),
                'duration_hours': duration_mins // 60,
                'capacity': capacity,
                'current_count': current_count,
                'status_class': status_class,
                'created_at': created_at
            })
        
        return render_template('status.html', schedules=schedule_list)
    
    except Exception as e:
        current_app.logger.error(f"Status page error: {str(e)}", exc_info=True)
        return f"<h1>서버 에러</h1><p>{str(e)}</p>", 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/admin/errors')
def admin_errors():
    """
    관리자 에러 대시보드
    
    URL: https://yourusername.pythonanywhere.com/web/admin/errors
    
    로그 파일에서 최근 50개 에러 표시
    
    Returns:
        HTML: 에러 로그 테이블
    """
    try:
        # 로그 파일 읽기
        with open('logs/error.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 최근 50개만
        recent_lines = lines[-50:] if len(lines) > 50 else lines
        recent_lines.reverse()  # 최신순
        
        # 에러만 필터링
        error_logs = []
        for line in recent_lines:
            if 'ERROR' in line:
                error_logs.append(line.strip())
        
        return render_template('admin_errors.html', logs=error_logs)
    
    except FileNotFoundError:
        return "<h1>로그 파일이 없습니다</h1>", 404
    except Exception as e:
        current_app.logger.error(f"Admin errors page error: {str(e)}", exc_info=True)
        return f"<h1>서버 에러</h1><p>{str(e)}</p>", 500
