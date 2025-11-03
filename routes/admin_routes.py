"""
관리자 라우트 (디버깅 로깅 추가)

관리자 전용 API 엔드포인트
- /admin/register: 스케줄 등록
- /admin/modify: 스케줄 수정 (통합)
- /admin/delete: 스케줄 삭제
- /admin/add_admin: 관리자 추가
- /admin/remove_admin: 관리자 삭제
"""

from flask import Blueprint, request, current_app
from utils.db import get_db_connection
from utils.kakao_response import simple_text
from utils.datetime_parser import (
    parse_admin_schedule, 
    parse_user_input,
    format_datetime_short, 
    format_datetime_korean,
    format_duration,
    extract_number
)
from datetime import datetime

bp = Blueprint('admin', __name__)


@bp.route('/admin/register', methods=['POST'])
def register_schedule():
    """
    관리자 스케줄 등록 API
    
    파라미터:
    - date_day: "27일" (필수)
    - week_day: "월요일" 또는 "월" (필수)
    - time_hour: "11시" (필수)
    - duration_hour: "4시간" (필수)
    - capacity_count: "5명" (필수)
    
    예시 발화: "27일 월요일 11시 4시간 5명"
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        
        params = data['action']['params']
        day = params.get('date_day')
        week_day = params.get('week_day')
        hour = params.get('time_hour')
        duration = params.get('duration_hour')
        capacity = params.get('capacity_count')
        
        # 로깅
        current_app.logger.info(
            f"API Call: /admin/register | User: {user_id} | "
            f"Params: day={day}, week={week_day}, hour={hour}, duration={duration}, capacity={capacity}"
        )
        
        # 필수 파라미터 체크
        if not all([day, week_day, hour, duration, capacity]):
            current_app.logger.warning(f"파라미터 누락 | User: {user_id}")
            return simple_text(
                "필수 정보가 누락되었습니다.\n"
                "예) 27일 월요일 11시 4시간 5명"
            )
        
        # DB 연결
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 관리자 권한 확인
        cursor.execute("SELECT * FROM admins WHERE user_id = %s", (user_id,))
        admin = cursor.fetchone()
        
        current_app.logger.info(f"관리자 조회: user_id={user_id}, is_admin={admin is not None}")
        
        if not admin:
            current_app.logger.warning(f"권한 거부: {user_id}")
            return simple_text("❌ 관리자 권한이 없습니다.")
        
        # 스케줄 파싱
        try:
            schedule_info = parse_admin_schedule(
                day=day, 
                hour=hour, 
                minute='0',
                duration=duration, 
                capacity=capacity
            )
            current_app.logger.info(f"스케줄 파싱 성공: {schedule_info}")
        except ValueError as e:
            current_app.logger.warning(f"파싱 실패: {str(e)}")
            return simple_text(f"❌ 입력 형식이 올바르지 않습니다.\n{str(e)}")
        
        # 중복 체크
        cursor.execute("""
            SELECT id FROM schedules 
            WHERE schedule_datetime = %s 
              AND duration_minutes = %s
        """, (schedule_info['schedule_datetime'], schedule_info['duration_minutes']))
        
        if cursor.fetchone():
            current_app.logger.warning(f"중복 스케줄: {schedule_info['schedule_datetime']}")
            return simple_text(
                "⚠️ 이미 해당 시간에 동일한 스케줄이 존재합니다.\n\n"
                f"📅 {format_datetime_korean(schedule_info['schedule_datetime'])}\n"
                f"⏰ 근무시간: {format_duration(schedule_info['duration_minutes'])}"
            )
        
        # 스케줄 등록
        cursor.execute("""
            INSERT INTO schedules 
            (schedule_datetime, duration_minutes, capacity, current_count)
            VALUES (%s, %s, %s, 0)
        """, (
            schedule_info['schedule_datetime'],
            schedule_info['duration_minutes'],
            schedule_info['capacity']
        ))
        
        conn.commit()
        
        current_app.logger.info(
            f"✅ 스케줄 등록 완료 | User: {user_id} | DateTime: {schedule_info['schedule_datetime']}"
        )
        
        return simple_text(
            f"✅ 스케줄이 등록되었습니다!\n\n"
            f"📅 {format_datetime_korean(schedule_info['schedule_datetime'])}\n"
            f"⏰ 근무시간: {format_duration(schedule_info['duration_minutes'])}\n"
            f"👥 정원: {schedule_info['capacity']}명"
        )
    
    except ValueError as e:
        current_app.logger.warning(f"파라미터 파싱 에러: {str(e)}")
        return simple_text(f"❌ 입력 형식이 올바르지 않습니다.\n{str(e)}")
    
    except Exception as e:
        current_app.logger.error(f"❌ 스케줄 등록 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 스케줄 등록에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route('/admin/modify', methods=['POST'])
def modify_schedule():
    """
    스케줄 수정 API (통합)
    
    파라미터:
    - date_day: "3일" (필수)
    - week_day: "월요일" 또는 "월" (필수)
    - time_hour: "11시" (필수)
    - duration_hour: "8시간" (필수)
    - capacity_count: "5명" (필수)
    
    예시 발화: "3일 월요일 11시 8시간 5명 변경"
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        
        params = data['action']['params']
        day = params.get('date_day')
        week_day = params.get('week_day')
        hour = params.get('time_hour')
        duration = params.get('duration_hour')
        capacity = params.get('capacity_count')
        
        current_app.logger.info(
            f"API Call: /admin/modify | User: {user_id} | "
            f"Params: day={day}, week={week_day}, hour={hour}, duration={duration}, capacity={capacity}"
        )
        
        if not all([day, week_day, hour, duration, capacity]):
            current_app.logger.warning(f"파라미터 누락 | User: {user_id}")
            return simple_text(
                "필수 정보가 누락되었습니다.\n"
                "예) 3일 월요일 11시 8시간 5명 변경"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 관리자 권한 확인
        cursor.execute("SELECT * FROM admins WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            current_app.logger.warning(f"권한 거부: {user_id}")
            return simple_text("❌ 관리자 권한이 없습니다.")
        
        # 숫자 추출
        day_num = extract_number(day)
        hour_num = extract_number(hour)
        duration_num = extract_number(duration)
        capacity_num = extract_number(capacity)
        
        # 날짜 계산
        today = datetime.now()
        if today.day <= day_num:
            search_date = datetime(today.year, today.month, day_num, hour_num, 0, 0)
        else:
            if today.month == 12:
                search_date = datetime(today.year + 1, 1, day_num, hour_num, 0, 0)
            else:
                search_date = datetime(today.year, today.month + 1, day_num, hour_num, 0, 0)
        
        # 기존 스케줄 검색
        cursor.execute("""
            SELECT * FROM schedules 
            WHERE DATE(schedule_datetime) = DATE(%s)
              AND HOUR(schedule_datetime) = %s
            LIMIT 1
        """, (search_date, hour_num))
        
        schedule = cursor.fetchone()
        
        if not schedule:
            current_app.logger.warning(f"스케줄 없음: {search_date}")
            return simple_text(
                f"❌ 해당 스케줄을 찾을 수 없습니다.\n\n"
                f"📅 {day_num}일 ({week_day}) {hour_num}시"
            )
        
        # 정원 체크
        if capacity_num < schedule['current_count']:
            current_app.logger.warning(
                f"정원 초과: current={schedule['current_count']}, new={capacity_num}"
            )
            return simple_text(
                f"❌ 현재 신청자({schedule['current_count']}명)보다\n"
                f"작은 정원({capacity_num}명)으로 변경할 수 없습니다."
            )
        
        # 업데이트
        cursor.execute("""
            UPDATE schedules 
            SET duration_minutes = %s,
                capacity = %s
            WHERE id = %s
        """, (duration_num * 60, capacity_num, schedule['id']))
        
        conn.commit()
        
        # 업데이트된 정보 조회
        cursor.execute("SELECT * FROM schedules WHERE id = %s", (schedule['id'],))
        updated = cursor.fetchone()
        
        current_app.logger.info(f"✅ 스케줄 수정 완료 | ID: {schedule['id']}")
        
        return simple_text(
            f"✅ 스케줄이 수정되었습니다!\n\n"
            f"📅 {format_datetime_korean(updated['schedule_datetime'])}\n"
            f"⏰ 근무시간: {format_duration(updated['duration_minutes'])}\n"
            f"👥 정원: {updated['capacity']}명\n"
            f"현재 신청자: {updated['current_count']}명"
        )
    
    except ValueError as e:
        current_app.logger.warning(f"파라미터 파싱 에러: {str(e)}")
        return simple_text(f"❌ 입력 형식이 올바르지 않습니다.\n{str(e)}")
    
    except Exception as e:
        current_app.logger.error(f"❌ 스케줄 수정 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 스케줄 수정에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route('/admin/delete', methods=['POST'])
def delete_schedule():
    """
    스케줄 삭제 API
    
    파라미터:
    - date_day: "27일" (필수)
    - week_day: "월요일" (필수)
    - time_hour: "11시" (필수)
    - duration_hour: "4시간" (필수)
    
    예시 발화: "27일 월요일 11시 4시간 삭제"
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        
        params = data['action']['params']
        day = params.get('date_day')
        week_day = params.get('week_day')
        hour = params.get('time_hour')
        duration = params.get('duration_hour')
        
        current_app.logger.info(
            f"API Call: /admin/delete | User: {user_id} | "
            f"Params: day={day}, week={week_day}, hour={hour}, duration={duration}"
        )
        
        if not all([day, week_day, hour, duration]):
            current_app.logger.warning(f"파라미터 누락 | User: {user_id}")
            return simple_text(
                "필수 정보가 누락되었습니다.\n"
                "예) 27일 월요일 11시 4시간 삭제"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 관리자 권한 확인
        cursor.execute("SELECT * FROM admins WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            current_app.logger.warning(f"권한 거부: {user_id}")
            return simple_text("❌ 관리자 권한이 없습니다.")
        
        # 스케줄 검색
        try:
            parsed = parse_user_input(day, hour, minute='0', duration=duration)
            target_datetime = parsed['schedule_datetime']
            duration_minutes = parsed['duration_minutes']
        except ValueError as e:
            current_app.logger.warning(f"파싱 실패: {str(e)}")
            return simple_text(f"❌ 입력 형식이 올바르지 않습니다.\n{str(e)}")
        
        cursor.execute("""
            SELECT * FROM schedules 
            WHERE schedule_datetime = %s 
              AND duration_minutes = %s
        """, (target_datetime, duration_minutes))
        
        schedule = cursor.fetchone()
        
        if not schedule:
            current_app.logger.warning(f"스케줄 없음: {target_datetime}")
            return simple_text(f"❌ 해당 스케줄을 찾을 수 없습니다.")
        
        # 관련 신청 삭제
        cursor.execute("DELETE FROM applications WHERE schedule_id = %s", (schedule['id'],))
        
        # 스케줄 삭제
        cursor.execute("DELETE FROM schedules WHERE id = %s", (schedule['id'],))
        
        conn.commit()
        
        current_app.logger.info(f"✅ 스케줄 삭제 완료 | ID: {schedule['id']}")
        
        return simple_text(
            f"✅ 스케줄이 삭제되었습니다.\n\n"
            f"📅 {format_datetime_short(schedule['schedule_datetime'])}\n"
            f"⏰ 근무시간: {format_duration(schedule['duration_minutes'])}\n"
            f"(신청자 {schedule['current_count']}명 함께 삭제됨)"
        )
    
    except Exception as e:
        current_app.logger.error(f"❌ 스케줄 삭제 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 스케줄 삭제에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route('/admin/add_admin', methods=['POST'])
def add_admin():
    """
    관리자 추가 API
    
    발화: "관리자 추가 {user_id} {nickname}"
    예시: "관리자 추가 user123 김철수"
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        utterance = data['userRequest']['utterance']
        
        current_app.logger.info(
            f"API Call: /admin/add_admin | User: {user_id} | Utterance: {utterance}"
        )
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 슈퍼 관리자 확인
        cursor.execute("""
            SELECT * FROM admins 
            WHERE user_id = %s AND added_by = 'system'
        """, (user_id,))
        
        if not cursor.fetchone():
            current_app.logger.warning(f"슈퍼 관리자 아님: {user_id}")
            return simple_text("❌ 슈퍼 관리자 권한이 필요합니다.")
        
        # 발화 파싱
        parts = utterance.split()
        if len(parts) < 3:
            current_app.logger.warning(f"파싱 실패: {utterance}")
            return simple_text(
                "입력 형식이 올바르지 않습니다.\n"
                "예) 관리자 추가 user123 김철수"
            )
        
        new_admin_id = parts[2]
        new_admin_nickname = parts[3] if len(parts) > 3 else "관리자"
        
        # 사용자 등록 또는 업데이트
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (new_admin_id,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (user_id, nickname) VALUES (%s, %s)",
                (new_admin_id, new_admin_nickname)
            )
        
        # 관리자 등록
        cursor.execute("""
            INSERT INTO admins (user_id, added_by) 
            VALUES (%s, %s)
        """, (new_admin_id, user_id))
        
        conn.commit()
        
        current_app.logger.info(f"✅ 관리자 추가 완료: {new_admin_id}")
        
        return simple_text(
            f"✅ 관리자가 추가되었습니다!\n\n"
            f"👤 User ID: {new_admin_id}\n"
            f"📛 닉네임: {new_admin_nickname}"
        )
    
    except Exception as e:
        current_app.logger.error(f"❌ 관리자 추가 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 관리자 추가에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@bp.route('/admin/remove_admin', methods=['POST'])
def remove_admin():
    """
    관리자 삭제 API
    
    발화: "관리자 삭제 {user_id}"
    예시: "관리자 삭제 user123"
    """
    conn = None
    cursor = None
    
    try:
        data = request.json
        user_id = data['userRequest']['user']['id']
        utterance = data['userRequest']['utterance']
        
        current_app.logger.info(
            f"API Call: /admin/remove_admin | User: {user_id} | Utterance: {utterance}"
        )
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 슈퍼 관리자 확인
        cursor.execute("""
            SELECT * FROM admins 
            WHERE user_id = %s AND added_by = 'system'
        """, (user_id,))
        
        if not cursor.fetchone():
            current_app.logger.warning(f"슈퍼 관리자 아님: {user_id}")
            return simple_text("❌ 슈퍼 관리자 권한이 필요합니다.")
        
        # 발화 파싱
        parts = utterance.split()
        if len(parts) < 3:
            current_app.logger.warning(f"파싱 실패: {utterance}")
            return simple_text(
                "입력 형식이 올바르지 않습니다.\n"
                "예) 관리자 삭제 user123"
            )
        
        target_admin_id = parts[2]
        
        # 본인 삭제 방지
        if target_admin_id == user_id:
            current_app.logger.warning(f"본인 삭제 시도: {user_id}")
            return simple_text("❌ 본인을 삭제할 수 없습니다.")
        
        # 관리자 삭제
        cursor.execute("DELETE FROM admins WHERE user_id = %s", (target_admin_id,))
        
        if cursor.rowcount == 0:
            current_app.logger.warning(f"관리자 아님: {target_admin_id}")
            return simple_text(f"❌ {target_admin_id}는 관리자가 아닙니다.")
        
        conn.commit()
        
        current_app.logger.info(f"✅ 관리자 삭제 완료: {target_admin_id}")
        
        return simple_text(
            f"✅ 관리자가 삭제되었습니다.\n\n"
            f"👤 User ID: {target_admin_id}"
        )
    
    except Exception as e:
        current_app.logger.error(f"❌ 관리자 삭제 실패: {str(e)}", exc_info=True)
        return simple_text("❌ 관리자 삭제에 실패했습니다.")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
