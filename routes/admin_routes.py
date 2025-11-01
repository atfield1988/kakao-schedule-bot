"""
관리자 API 라우트

- 스케줄 등록 (부분 성공)
- 스케줄 수정 (시간 변경: 컨텍스트 2단계, 인원 변경: 검증)
- 스케줄 삭제 (CASCADE)
- 관리자 추가/삭제 (슈퍼 관리자 전용)
- 관리자 현황
"""

from flask import Blueprint, request, jsonify, current_app
from utils.db import get_db_connection
from utils.datetime_parser import parse_admin_schedule, parse_user_input, format_datetime_short
from utils.kakao_response import simple_text, context_response
from utils.auth import is_admin, is_super_admin
from utils.validators import validate_capacity_change
from utils.logging_setup import log_admin_action
import re

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/register', methods=['POST'])
def register_schedule():
    """
    스케줄 등록 (부분 성공 지원)
    
    카카오톡 발화: 
        단일: "27일 월 11시 4시간 4명"
        여러개: "27일 월 11시 4시간 4명\n27일 월 17시 4시간 5명"
    
    핵심 로직:
        1. 관리자 권한 확인
        2. 여러 줄 파싱
        3. 각 줄마다 INSERT 시도
        4. 성공/실패 리스트 반환 (부분 성공)
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    # 관리자 권한 확인
    if not is_admin(user_id):
        return jsonify(simple_text("❌ 관리자 권한이 필요합니다.")), 403
    
    utterance = data['userRequest']['utterance']
    
    # 파라미터 추출 (단일 등록)
    params = data.get('action', {}).get('params', {})
    
    # 여러 줄 입력 처리
    lines = utterance.strip().split('\n')
    success_list = []
    failed_list = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        for idx, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            
            # 정규식: "27일 월 11시 4시간 4명"
            # 분 단위 지원: "27일 월 11시 30분 4시간 4명"
            match = re.match(
                r'(\d+)일\s*(\w)\s*(\d+)시\s*(?:(\d+)분\s*)?(\d+)시간\s*(\d+)명',
                line
            )
            
            if not match:
                failed_list.append(f"{idx}번째 줄: 형식 오류")
                continue
            
            day = match.group(1)
            day_of_week = match.group(2)
            hour = match.group(3)
            minute = match.group(4) or '0'
            duration = match.group(5)
            capacity = match.group(6)
            
            # 파싱
            schedule_data = parse_admin_schedule(
                day, day_of_week, hour, minute, duration, capacity
            )
            
            if not schedule_data:
                failed_list.append(f"{idx}번째 줄: 잘못된 날짜")
                continue
            
            # DB 삽입
            try:
                cursor.execute("""
                    INSERT INTO schedules (schedule_datetime, duration_minutes, capacity)
                    VALUES (%s, %s, %s)
                """, (
                    schedule_data['schedule_datetime'],
                    schedule_data['duration_minutes'],
                    schedule_data['capacity']
                ))
                success_list.append(
                    f"{format_datetime_short(schedule_data['schedule_datetime'])} "
                    f"({schedule_data['capacity']}명)"
                )
            except Exception as e:
                failed_list.append(f"{idx}번째 줄: DB 오류 ({str(e)[:30]})")
        
        conn.commit()
        
        # 응답 생성
        response = f"✅ {len(success_list)}개 스케줄 등록 완료\n\n"
        
        if success_list:
            response += "등록된 스케줄:\n"
            response += "\n".join(f"• {s}" for s in success_list)
        
        if failed_list:
            response += "\n\n❌ 실패:\n"
            response += "\n".join(f"• {f}" for f in failed_list)
        
        log_admin_action(
            current_app, 
            "REGISTER_SCHEDULE", 
            user_id, 
            {'success': len(success_list), 'failed': len(failed_list)}
        )
        
        return jsonify(simple_text(response))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Register error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/modify/select', methods=['POST'])
def modify_select():
    """
    스케줄 수정 - 1단계: 수정 대상 선택
    
    카카오톡 발화: "27일 11시 변경"
    
    핵심 로직:
        1. 범위 검색으로 스케줄 찾기
        2. 현재 신청자 수 확인
        3. 컨텍스트에 schedule_id 저장
        4. 2단계로 유도
    
    Returns:
        JSON: 컨텍스트 포함 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    if not is_admin(user_id):
        return jsonify(simple_text("❌ 관리자 권한이 필요합니다.")), 403
    
    params = data.get('action', {}).get('params', {})
    day = params.get('@date_day')
    hour = params.get('@time_hour')
    
    if not day or not hour:
        return jsonify(simple_text("날짜 형식이 잘못되었습니다."))
    
    # 범위 검색
    date_range = parse_user_input(day, hour)
    if not date_range:
        return jsonify(simple_text("잘못된 날짜입니다."))
    
    start_dt, end_dt = date_range
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, schedule_datetime, capacity, current_count
            FROM schedules
            WHERE schedule_datetime >= %s AND schedule_datetime < %s
        """, (start_dt, end_dt))
        
        schedule = cursor.fetchone()
        
        if not schedule:
            return jsonify(simple_text("해당 스케줄을 찾을 수 없습니다."))
        
        schedule_id, schedule_dt, capacity, current_count = schedule
        
        # 컨텍스트 응답
        return jsonify(context_response(
            f"✅ [{format_datetime_short(schedule_dt)}] 스케줄을 찾았습니다.\n"
            f"현재 신청자: {current_count}명\n\n"
            f"새로운 날짜와 시간을 입력해주세요.\n"
            f"(예: 27일 13시 또는 27일 13시 30분)",
            "ModifySchedule",
            1,  # 다음 1번 대화에서만 유효
            {
                "schedule_id": schedule_id,
                "original_datetime": format_datetime_short(schedule_dt),
                "action": "modify_time"
            }
        ))
    
    except Exception as e:
        current_app.logger.error(f"Modify select error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/modify/execute', methods=['POST'])
def modify_execute():
    """
    스케줄 수정 - 2단계: 시간 변경 실행
    
    카카오톡 발화: "27일 13시" (컨텍스트 있는 상태)
    
    핵심 로직:
        1. 컨텍스트에서 schedule_id 추출
        2. 새로운 날짜/시간 파싱
        3. UPDATE schedules
        4. 기존 신청자는 자동으로 새 시간으로 이동
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    if not is_admin(user_id):
        return jsonify(simple_text("❌ 관리자 권한이 필요합니다.")), 403
    
    # 컨텍스트 추출
    contexts = data.get('contexts', [])
    modify_context = next(
        (c for c in contexts if c['name'] == 'ModifySchedule'),
        None
    )
    
    if not modify_context:
        return jsonify(simple_text(
            "수정할 스케줄을 먼저 선택해주세요.\n"
            "(예: '27일 11시 변경')"
        ))
    
    schedule_id = modify_context['params']['schedule_id']
    original_datetime = modify_context['params']['original_datetime']
    
    # 새로운 날짜/시간 파싱
    params = data.get('action', {}).get('params', {})
    new_day = params.get('@date_day')
    new_hour = params.get('@time_hour')
    new_minute = params.get('@time_minute', 0)
    
    if not new_day or not new_hour:
        return jsonify(simple_text("날짜 형식이 잘못되었습니다."))
    
    # 파싱
    date_range = parse_user_input(new_day, new_hour, new_minute)
    if not date_range:
        return jsonify(simple_text("잘못된 날짜입니다."))
    
    new_datetime, _ = date_range
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 시간 변경
        cursor.execute("""
            UPDATE schedules
            SET schedule_datetime = %s
            WHERE id = %s
        """, (new_datetime, schedule_id))
        
        conn.commit()
        
        # 신청자 목록 조회
        cursor.execute("""
            SELECT u.nickname
            FROM applications a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.schedule_id = %s
        """, (schedule_id,))
        
        applicants = [row[0] for row in cursor.fetchall()]
        applicant_str = ", ".join(applicants) if applicants else "없음"
        
        log_admin_action(
            current_app,
            "MODIFY_TIME",
            user_id,
            {'schedule_id': schedule_id, 'new_time': str(new_datetime)}
        )
        
        return jsonify(simple_text(
            f"✅ [{original_datetime}] 스케줄이\n"
            f"   [{format_datetime_short(new_datetime)}]로 변경되었습니다.\n\n"
            f"기존 신청자({len(applicants)}명)도 함께 이동되었습니다:\n"
            f"{applicant_str}"
        ))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Modify execute error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/modify/capacity', methods=['POST'])
def modify_capacity():
    """
    스케줄 인원 변경 (검증 포함)
    
    카카오톡 발화: "27일 11시 인원 6명"
    
    핵심 로직:
        1. 범위 검색으로 스케줄 찾기
        2. 현재 신청자 수 확인
        3. 검증: 신청자 수보다 적게 줄일 수 없음
        4. UPDATE schedules
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    if not is_admin(user_id):
        return jsonify(simple_text("❌ 관리자 권한이 필요합니다.")), 403
    
    params = data.get('action', {}).get('params', {})
    day = params.get('@date_day')
    hour = params.get('@time_hour')
    new_capacity = params.get('@capacity_count')
    
    if not day or not hour or not new_capacity:
        return jsonify(simple_text("형식이 잘못되었습니다."))
    
    new_capacity = int(new_capacity)
    
    # 범위 검색
    date_range = parse_user_input(day, hour)
    if not date_range:
        return jsonify(simple_text("잘못된 날짜입니다."))
    
    start_dt, end_dt = date_range
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, schedule_datetime, capacity, current_count
            FROM schedules
            WHERE schedule_datetime >= %s AND schedule_datetime < %s
        """, (start_dt, end_dt))
        
        schedule = cursor.fetchone()
        
        if not schedule:
            return jsonify(simple_text("해당 스케줄을 찾을 수 없습니다."))
        
        schedule_id, schedule_dt, old_capacity, current_count = schedule
        
        # 검증: 신청자보다 적게 줄일 수 없음
        is_valid, error_msg = validate_capacity_change(current_count, new_capacity)
        
        if not is_valid:
            return jsonify(simple_text(f"❌ {error_msg}"))
        
        # 인원 변경
        cursor.execute("""
            UPDATE schedules
            SET capacity = %s
            WHERE id = %s
        """, (new_capacity, schedule_id))
        
        conn.commit()
        
        log_admin_action(
            current_app,
            "MODIFY_CAPACITY",
            user_id,
            {'schedule_id': schedule_id, 'old': old_capacity, 'new': new_capacity}
        )
        
        return jsonify(simple_text(
            f"✅ [{format_datetime_short(schedule_dt)}] 정원이\n"
            f"   {old_capacity}명 → {new_capacity}명으로 변경되었습니다.\n"
            f"현재 신청: {current_count}명"
        ))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Modify capacity error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/delete', methods=['POST'])
def delete_schedule():
    """
    스케줄 삭제 (CASCADE)
    
    카카오톡 발화: "27일 11시 삭제"
    
    핵심 로직:
        1. 범위 검색으로 스케줄 찾기
        2. DELETE schedules (CASCADE로 applications 자동 삭제)
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    if not is_admin(user_id):
        return jsonify(simple_text("❌ 관리자 권한이 필요합니다.")), 403
    
    params = data.get('action', {}).get('params', {})
    day = params.get('@date_day')
    hour = params.get('@time_hour')
    
    if not day or not hour:
        return jsonify(simple_text("날짜 형식이 잘못되었습니다."))
    
    # 범위 검색
    date_range = parse_user_input(day, hour)
    if not date_range:
        return jsonify(simple_text("잘못된 날짜입니다."))
    
    start_dt, end_dt = date_range
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, schedule_datetime, current_count
            FROM schedules
            WHERE schedule_datetime >= %s AND schedule_datetime < %s
        """, (start_dt, end_dt))
        
        schedule = cursor.fetchone()
        
        if not schedule:
            return jsonify(simple_text("해당 스케줄을 찾을 수 없습니다."))
        
        schedule_id, schedule_dt, current_count = schedule
        
        # 삭제 (CASCADE)
        cursor.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,))
        
        conn.commit()
        
        log_admin_action(
            current_app,
            "DELETE_SCHEDULE",
            user_id,
            {'schedule_id': schedule_id, 'applicants': current_count}
        )
        
        return jsonify(simple_text(
            f"✅ [{format_datetime_short(schedule_dt)}] 스케줄이 삭제되었습니다.\n"
            f"(신청자 {current_count}명의 신청도 함께 삭제됨)"
        ))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Delete error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/add_admin', methods=['POST'])
def add_admin():
    """
    관리자 추가 (슈퍼 관리자 전용)
    
    카카오톡 발화: "관리자 추가 user123 김철수"
    
    핵심 로직:
        1. 슈퍼 관리자 권한 확인
        2. 파라미터 파싱 (정규식)
        3. users 테이블 확인/추가
        4. admins 테이블 추가
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    current_user_id = data['userRequest']['user']['id']
    
    # 슈퍼 관리자 권한 확인
    if not is_super_admin(current_user_id):
        return jsonify(simple_text("❌ 슈퍼 관리자만 사용 가능합니다.")), 403
    
    utterance = data['userRequest']['utterance']
    
    # 파싱: "관리자 추가 user123 김철수"
    match = re.match(r'관리자\s+추가\s+(\S+)\s+(.+)', utterance)
    
    if not match:
        return jsonify(simple_text(
            "❌ 형식 오류\n"
            "사용법: 관리자 추가 [user_id] [닉네임]\n"
            "예시: 관리자 추가 user123 김철수"
        ))
    
    new_user_id = match.group(1)
    nickname = match.group(2)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # users 테이블 확인
        cursor.execute("SELECT nickname FROM users WHERE user_id = %s", (new_user_id,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            existing_nickname = existing_user[0]
        else:
            # 신규 유저 등록
            cursor.execute(
                "INSERT INTO users (user_id, nickname) VALUES (%s, %s)",
                (new_user_id, nickname)
            )
            existing_nickname = nickname
        
        # admins 테이블 확인
        cursor.execute("SELECT 1 FROM admins WHERE user_id = %s", (new_user_id,))
        if cursor.fetchone():
            conn.rollback()
            return jsonify(simple_text(
                f"⚠️ '{existing_nickname}'님은 이미 관리자입니다."
            ))
        
        # 관리자 추가
        cursor.execute(
            "INSERT INTO admins (user_id, added_by) VALUES (%s, %s)",
            (new_user_id, current_user_id)
        )
        
        conn.commit()
        
        log_admin_action(
            current_app,
            "ADD_ADMIN",
            current_user_id,
            {'new_admin': new_user_id}
        )
        
        return jsonify(simple_text(
            f"✅ '{existing_nickname}'님을 관리자로 추가했습니다.\n"
            f"User ID: {new_user_id}"
        ))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Add admin error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/remove_admin', methods=['POST'])
def remove_admin():
    """
    관리자 삭제 (슈퍼 관리자 전용)
    
    카카오톡 발화: "관리자 삭제 user123"
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    current_user_id = data['userRequest']['user']['id']
    
    if not is_super_admin(current_user_id):
        return jsonify(simple_text("❌ 슈퍼 관리자만 사용 가능합니다.")), 403
    
    utterance = data['userRequest']['utterance']
    match = re.match(r'관리자\s+삭제\s+(\S+)', utterance)
    
    if not match:
        return jsonify(simple_text(
            "❌ 형식 오류\n사용법: 관리자 삭제 [user_id]"
        ))
    
    target_user_id = match.group(1)
    
    # 자기 자신 삭제 방지
    if target_user_id == current_user_id:
        return jsonify(simple_text("❌ 자기 자신은 삭제할 수 없습니다."))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT nickname FROM users WHERE user_id = %s", (target_user_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify(simple_text("❌ 존재하지 않는 사용자입니다."))
        
        nickname = result[0]
        
        cursor.execute("DELETE FROM admins WHERE user_id = %s", (target_user_id,))
        
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify(simple_text(f"⚠️ '{nickname}'님은 관리자가 아닙니다."))
        
        conn.commit()
        
        log_admin_action(
            current_app,
            "REMOVE_ADMIN",
            current_user_id,
            {'removed_admin': target_user_id}
        )
        
        return jsonify(simple_text(
            f"✅ '{nickname}'님의 관리자 권한을 회수했습니다."
        ))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Remove admin error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()
