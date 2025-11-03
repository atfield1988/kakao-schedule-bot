"""
사용자 라우트

일반 사용자가 사용하는 API 엔드포인트
- /welcome: 환영 메시지 + 닉네임 등록
- /apply: 스케줄 신청
- /user/applications: 내 신청 내역
- /cancel: 신청 취소
- /status: 전체 현황 조회
"""

from flask import Blueprint, request, current_app
from utils.db import get_db_connection
from utils.kakao_response import simple_text, list_card
from utils.datetime_parser import parse_user_input, format_datetime_short, format_duration
from datetime import datetime

bp = Blueprint('user', __name__)


@bp.route('/welcome', methods=['POST'])
def welcome():
    """
    환영 메시지 API + 닉네임 등록
    
    첫 방문 시:
    1. "안녕" 입력 → 닉네임 입력 요청
    2. "채희" 입력 → 닉네임 등록 완료
    
    기존 사용자:
    - "안녕" 입력 → 환영 메시지 표시
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        utterance = data['userRequest']['utterance']
        
        current_app.logger.info(f"API Call: /welcome | User: {user_id} | Utterance: {utterance}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 사용자 조회
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        # 첫 방문 (닉네임 없음)
        if not user:
            # 기본 명령어인지 확인
            if utterance.strip() in ['안녕', '시작', '도와줘', '도움말']:
                return simple_text(
                    "👋 환영합니다!\n\n"
                    "스케줄 신청 시스템을 사용하시려면\n"
                    "닉네임을 입력해주세요.\n\n"
                    "예) 채희"
                )
            else:
                # 발화를 닉네임으로 등록
                nickname = utterance.strip()
                
                cursor.execute(
                    "INSERT INTO users (user_id, nickname) VALUES (%s, %s)",
                    (user_id, nickname)
                )
                conn.commit()
                
                current_app.logger.info(f"신규 사용자 등록: {user_id} ({nickname})")
                
                return simple_text(
                    f"✅ {nickname}님, 환영합니다!\n\n"
                    "📅 스케줄 신청 시스템입니다.\n\n"
                    "[사용 방법]\n"
                    "• 신청: 14일 월 14시 8시간\n"
                    "• 취소: 취소\n"
                    "• 현황: 결과\n\n"
                    "원하시는 명령어를 입력해주세요!"
                )
        
        # 기존 사용자
        nickname = user['nickname']
        
        message = (
            f"안녕하세요, {nickname}님! 👋\n\n"
            "📅 스케줄 신청 시스템입니다.\n\n"
            "[사용 방법]\n"
            "• 신청: 14일 월 14시 8시간\n"
            "• 취소: 취소\n"
            "• 현황: 결과\n\n"
            "원하시는 명령어를 입력해주세요!"
        )
        
        return simple_text(message)
    
    except Exception as e:
        current_app.logger.error(f"Welcome 에러: {str(e)}", exc_info=True)
        return simple_text("❌ 서버 에러가 발생했습니다. 잠시 후 다시 시도해주세요.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route('/apply', methods=['POST'])
def apply_schedule():
    """
    스케줄 신청 API
    
    파라미터:
    - date_day: "14일" (필수)
    - week_day: "월요일" 또는 "월" (필수, 검증 없음 - 참고용)
    - time_hour: "14시" (필수)
    - duration_hour: "8시간" (필수)
    
    예시 발화: "14일 월 14시 8시간 신청"
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        
        # 파라미터 추출
        params = data['action']['params']
        day = params.get('date_day')
        week_day = params.get('week_day')
        hour = params.get('time_hour')
        duration = params.get('duration_hour')
        
        # 로깅
        current_app.logger.info(
            f"API Call: /apply | User: {user_id} | "
            f"Params: day={day}, week={week_day}, hour={hour}, duration={duration}"
        )
        
        # 필수 파라미터 체크
        if not all([day, week_day, hour, duration]):
            return simple_text(
                "필수 정보가 누락되었습니다.\n"
                "예) 14일 월 14시 8시간 신청"
            )
        
        # 날짜 파싱 (minute=0 고정)
        parsed = parse_user_input(day, hour, minute='0', duration=duration)
        target_datetime = parsed['schedule_datetime']
        duration_minutes = parsed['duration_minutes']
        
        # DB 연결
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 사용자 정보 조회
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            # Welcome 거치지 않은 경우 임시 닉네임
            cursor.execute(
                "INSERT INTO users (user_id, nickname) VALUES (%s, %s)",
                (user_id, f"유저{user_id[:6]}")
            )
            conn.commit()
            
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
        
        # 스케줄 검색 (정확한 시간 + 근무시간 매칭)
        cursor.execute("""
            SELECT * FROM schedules 
            WHERE schedule_datetime = %s 
              AND duration_minutes = %s
        """, (target_datetime, duration_minutes))
        
        schedule = cursor.fetchone()
        
        if not schedule:
            return simple_text(
                "❌ 존재하지 않는 스케줄입니다.\n\n"
                f"📅 {format_datetime_short(target_datetime)}\n"
                f"⏰ 근무시간: {format_duration(duration_minutes)}\n\n"
                "'결과' 명령어로 현황을 확인해주세요."
            )
        
        # 정원 확인
        if schedule['current_count'] >= schedule['capacity']:
            return simple_text(
                "😢 신청 마감되었습니다.\n\n"
                f"📅 {format_datetime_short(target_datetime)}\n"
                f"👥 정원: {schedule['current_count']}/{schedule['capacity']}명"
            )
        
        # 중복 신청 확인
        cursor.execute("""
            SELECT * FROM applications 
            WHERE user_id = %s AND schedule_id = %s
        """, (user_id, schedule['id']))
        
        if cursor.fetchone():
            return simple_text(
                "⚠️ 이미 신청한 스케줄입니다.\n\n"
                f"📅 {format_datetime_short(target_datetime)}"
            )
        
        # 신청 등록
        cursor.execute("""
            INSERT INTO applications (user_id, schedule_id)
            VALUES (%s, %s)
        """, (user_id, schedule['id']))
        
        # 스케줄 인원 업데이트
        cursor.execute("""
            UPDATE schedules 
            SET current_count = current_count + 1 
            WHERE id = %s
        """, (schedule['id'],))
        
        conn.commit()
        
        # 최신 정보 조회
        cursor.execute("SELECT * FROM schedules WHERE id = %s", (schedule['id'],))
        updated_schedule = cursor.fetchone()
        
        current_app.logger.info(
            f"신청 완료: User={user_id}, Schedule={schedule['id']}, "
            f"Count={updated_schedule['current_count']}/{updated_schedule['capacity']}"
        )
        
        return simple_text(
            f"✅ {user['nickname']}님, 신청이 완료되었습니다!\n\n"
            f"📅 {format_datetime_short(target_datetime)}\n"
            f"⏰ 근무시간: {format_duration(duration_minutes)}\n"
            f"👥 현재 인원: {updated_schedule['current_count']}/{updated_schedule['capacity']}명"
        )
    
    except ValueError as e:
        current_app.logger.warning(f"파라미터 파싱 에러: {str(e)}")
        return simple_text(f"❌ 입력 형식이 올바르지 않습니다.\n{str(e)}")
    
    except Exception as e:
        current_app.logger.error(f"신청 처리 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 신청 처리에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route('/user/applications', methods=['POST'])
def get_user_applications():
    """
    내 신청 내역 조회 API
    
    사용자가 "취소" 발화 시 호출
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        
        current_app.logger.info(f"API Call: /user/applications | User: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 신청 내역 조회
        cursor.execute("""
            SELECT 
                a.id AS application_id,
                s.schedule_datetime,
                s.duration_minutes,
                s.capacity,
                s.current_count
            FROM applications a
            JOIN schedules s ON a.schedule_id = s.id
            WHERE a.user_id = %s 
              AND s.schedule_datetime >= NOW()
            ORDER BY s.schedule_datetime
        """, (user_id,))
        
        applications = cursor.fetchall()
        
        if not applications:
            return simple_text(
                "📋 신청한 스케줄이 없습니다.\n\n"
                "스케줄을 신청하려면:\n"
                "예) 14일 월 14시 8시간"
            )
        
        # ListCard 생성
        items = []
        for app in applications:
            dt = app['schedule_datetime']
            
            items.append({
                "title": format_datetime_short(dt),
                "description": (
                    f"⏰ 근무시간: {format_duration(app['duration_minutes'])}\n"
                    f"👥 인원: {app['current_count']}/{app['capacity']}명"
                ),
                "action": "block",
                "blockId": "CANCEL_CONFIRM_BLOCK_ID",  # 실제 ID로 변경 필요
                "extra": {
                    "application_id": str(app['application_id'])
                }
            })
        
        return list_card(
            title="📋 내 신청 내역",
            items=items
        )
    
    except Exception as e:
        current_app.logger.error(f"신청 내역 조회 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 신청 내역 조회에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route('/cancel', methods=['POST'])
def cancel_application():
    """
    신청 취소 API
    
    ListCard에서 item 클릭 시 호출
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        
        # application_id 추출
        client_extra = data['action'].get('clientExtra', {})
        application_id = client_extra.get('application_id')
        
        if not application_id:
            params = data['action'].get('params', {})
            application_id = params.get('application_id')
        
        current_app.logger.info(
            f"API Call: /cancel | User: {user_id} | App ID: {application_id}"
        )
        
        if not application_id:
            return simple_text("❌ 취소할 신청을 선택해주세요.")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 신청 정보 조회
        cursor.execute("""
            SELECT a.*, s.schedule_datetime, s.duration_minutes
            FROM applications a
            JOIN schedules s ON a.schedule_id = s.id
            WHERE a.id = %s AND a.user_id = %s
        """, (application_id, user_id))
        
        application = cursor.fetchone()
        
        if not application:
            return simple_text("❌ 취소할 신청을 찾을 수 없습니다.")
        
        # 신청 삭제
        cursor.execute("DELETE FROM applications WHERE id = %s", (application_id,))
        
        # 스케줄 인원 감소
        cursor.execute("""
            UPDATE schedules 
            SET current_count = current_count - 1 
            WHERE id = %s
        """, (application['schedule_id'],))
        
        conn.commit()
        
        current_app.logger.info(
            f"신청 취소 완료: User={user_id}, Schedule={application['schedule_id']}"
        )
        
        return simple_text(
            f"✅ 신청이 취소되었습니다.\n\n"
            f"📅 {format_datetime_short(application['schedule_datetime'])}\n"
            f"⏰ 근무시간: {format_duration(application['duration_minutes'])}"
        )
    
    except Exception as e:
        current_app.logger.error(f"신청 취소 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 신청 취소에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route('/status', methods=['POST'])
def get_status():
    """
    전체 현황 조회 API
    
    사용자가 "결과" 발화 시 호출
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        
        current_app.logger.info(f"API Call: /status | User: {user_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 미래 스케줄 조회
        cursor.execute("""
            SELECT * FROM schedules 
            WHERE schedule_datetime >= NOW()
            ORDER BY schedule_datetime
            LIMIT 20
        """)
        
        schedules = cursor.fetchall()
        
        if not schedules:
            return simple_text(
                "📅 등록된 스케줄이 없습니다.\n\n"
                "관리자가 스케줄을 등록할 때까지 기다려주세요."
            )
        
        # ListCard 생성
        items = []
        for schedule in schedules:
            dt = schedule['schedule_datetime']
            
            # 상태 표시
            if schedule['current_count'] >= schedule['capacity']:
                status = "🔴 마감"
            elif schedule['current_count'] > 0:
                status = "🟡 모집중"
            else:
                status = "🟢 모집중"
            
            items.append({
                "title": f"{format_datetime_short(dt)} | {status}",
                "description": (
                    f"⏰ 근무시간: {format_duration(schedule['duration_minutes'])}\n"
                    f"👥 인원: {schedule['current_count']}/{schedule['capacity']}명"
                )
            })
        
        return list_card(
            title="📅 스케줄 현황",
            items=items
        )
    
    except Exception as e:
        current_app.logger.error(f"현황 조회 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 현황 조회에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
