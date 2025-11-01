"""
유저 API 라우트

- 닉네임 등록
- 신청 (범위 검색 + 트랜잭션)
- 취소 목록 (페이지네이션)
- 취소 실행
- 결과 조회
"""

from flask import Blueprint, request, jsonify, current_app
from utils.db import get_db_connection
from utils.datetime_parser import parse_user_input, format_datetime_short, format_datetime_korean
from utils.kakao_response import simple_text, list_card
from utils.logging_setup import log_api_call
from datetime import timedelta

bp = Blueprint('user', __name__)


@bp.route('/welcome', methods=['POST'])
def welcome():
    """
    환영 메시지 + 닉네임 등록
    
    카카오톡 발화: "안녕", "시작"
    
    Flow:
        1. user_id로 기존 유저 확인
        2. 신규 유저면 닉네임 입력 요청
        3. 기존 유저면 환영 메시지
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    utterance = data['userRequest']['utterance']
    
    log_api_call(current_app, '/welcome', user_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 기존 유저 확인
        cursor.execute("SELECT nickname FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result:
            # 기존 유저
            nickname = result[0]
            return jsonify(simple_text(
                f"안녕하세요, {nickname}님! 😊\n\n"
                "명령어:\n"
                "• '신청': 스케줄 신청 (예: 27일 11시)\n"
                "• '취소': 내 신청 내역 확인 및 취소\n"
                "• '결과': 전체 스케줄 현황 보기"
            ))
        else:
            # 신규 유저 - 닉네임 입력 요청
            # utterance가 "안녕"이 아니면 닉네임으로 등록
            if utterance in ["안녕", "시작", "도와줘", "도움말"]:
                return jsonify(simple_text(
                    "안녕하세요! 처음 오셨네요 😊\n\n"
                    "사용하실 이름을 입력해주세요."
                ))
            else:
                # 닉네임 등록
                nickname = utterance.strip()
                cursor.execute(
                    "INSERT INTO users (user_id, nickname) VALUES (%s, %s)",
                    (user_id, nickname)
                )
                conn.commit()
                
                current_app.logger.info(f"New user registered: {user_id} ({nickname})")
                
                return jsonify(simple_text(
                    f"환영합니다, {nickname}님! 🎉\n\n"
                    "명령어:\n"
                    "• '신청': 스케줄 신청 (예: 27일 11시)\n"
                    "• '취소': 내 신청 내역 확인 및 취소\n"
                    "• '결과': 전체 스케줄 현황 보기"
                ))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Welcome error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/apply', methods=['POST'])
def apply_schedule():
    """
    스케줄 신청 (핵심 동시성 처리)
    
    카카오톡 발화: "27일 11시", "1일 9시 신청"
    
    핵심 로직:
        1. 범위 검색으로 스케줄 찾기 (9시 → 9:00~9:59)
        2. SELECT ... FOR UPDATE로 행 잠금
        3. 정원 확인
        4. 중복 신청 확인
        5. 신청 처리 (current_count +1, applications 추가)
        6. 트랜잭션 커밋
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    # 파라미터 추출
    params = data.get('action', {}).get('params', {})
    day = params.get('@date_day') or params.get('date_day')
    hour = params.get('@time_hour') or params.get('time_hour')
    
    if not day or not hour:
        return jsonify(simple_text(
            "날짜 형식이 잘못되었습니다.\n"
            "'27일 11시' 형식으로 입력해주세요."
        ))
    
    log_api_call(current_app, '/apply', user_id, {'day': day, 'hour': hour})
    
    # 범위 검색 파싱
    date_range = parse_user_input(day, hour)
    if not date_range:
        return jsonify(simple_text("잘못된 날짜입니다."))
    
    start_dt, end_dt = date_range
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 스케줄 찾기 (범위 검색)
        cursor.execute("""
            SELECT id, schedule_datetime, duration_minutes, capacity, current_count
            FROM schedules
            WHERE schedule_datetime >= %s AND schedule_datetime < %s
        """, (start_dt, end_dt))
        
        schedule = cursor.fetchone()
        
        if not schedule:
            conn.rollback()
            return jsonify(simple_text("존재하지 않는 스케줄입니다."))
        
        schedule_id, schedule_dt, duration_mins, capacity, current_count = schedule
        
        # 2. SELECT FOR UPDATE (행 잠금 - 동시성 처리 핵심)
        cursor.execute("""
            SELECT current_count, capacity
            FROM schedules
            WHERE id = %s
            FOR UPDATE
        """, (schedule_id,))
        
        locked_row = cursor.fetchone()
        current_count, capacity = locked_row
        
        # 3. 정원 확인
        if current_count >= capacity:
            conn.rollback()
            return jsonify(simple_text(
                f"{format_datetime_short(schedule_dt)} 스케줄은 이미 마감되었습니다."
            ))
        
        # 4. 중복 신청 확인
        cursor.execute("""
            SELECT COUNT(*) FROM applications
            WHERE user_id = %s AND schedule_id = %s
        """, (user_id, schedule_id))
        
        if cursor.fetchone()[0] > 0:
            conn.rollback()
            return jsonify(simple_text("이미 신청한 시간대입니다."))
        
        # 5. 신청 처리
        cursor.execute("""
            UPDATE schedules
            SET current_count = current_count + 1
            WHERE id = %s
        """, (schedule_id,))
        
        cursor.execute("""
            INSERT INTO applications (user_id, schedule_id)
            VALUES (%s, %s)
        """, (user_id, schedule_id))
        
        # 6. 커밋
        conn.commit()
        
        # 닉네임 조회
        cursor.execute("SELECT nickname FROM users WHERE user_id = %s", (user_id,))
        nickname = cursor.fetchone()[0]
        
        current_app.logger.info(
            f"Application success: User={user_id} ({nickname}), Schedule={schedule_id}"
        )
        
        return jsonify(simple_text(
            f"✅ {nickname}님, 신청이 완료되었습니다!\n\n"
            f"📅 {format_datetime_korean(schedule_dt)}\n"
            f"⏰ 근무시간: {duration_mins // 60}시간\n"
            f"👥 현재 인원: {current_count + 1}/{capacity}명"
        ))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Apply error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/user/applications', methods=['POST'])
def get_user_applications():
    """
    유저 신청 내역 조회 (페이지네이션)
    
    카카오톡 발화: "취소"
    
    핵심 로직:
        1. 페이지 번호 추출 (기본 1)
        2. 페이지당 5개 항목 조회 (LIMIT/OFFSET)
        3. Items 배열로 신청 목록 생성 (클릭 가능)
        4. 이전/다음 페이지 버튼 추가
    
    Returns:
        JSON: ListCard 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    # 페이지 번호 (카카오 extra 파라미터)
    page = data.get('action', {}).get('params', {}).get('page', 1)
    page = int(page)
    per_page = 5  # 페이지당 항목 수
    
    log_api_call(current_app, '/user/applications', user_id, {'page': page})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 전체 신청 개수
        cursor.execute("""
            SELECT COUNT(*) FROM applications WHERE user_id = %s
        """, (user_id,))
        total_count = cursor.fetchone()[0]
        
        if total_count == 0:
            return jsonify(simple_text("신청 내역이 없습니다."))
        
        # 총 페이지 수
        total_pages = (total_count + per_page - 1) // per_page
        
        # 페이지네이션 쿼리
        cursor.execute("""
            SELECT a.id, s.schedule_datetime, s.duration_minutes
            FROM applications a
            JOIN schedules s ON a.schedule_id = s.id
            WHERE a.user_id = %s
            ORDER BY a.applied_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, per_page, (page - 1) * per_page))
        
        applications = cursor.fetchall()
        
        # Items 배열 생성 (클릭 가능)
        items = []
        for app_id, schedule_dt, duration_mins in applications:
            items.append({
                "title": format_datetime_korean(schedule_dt),
                "description": f"근무시간: {duration_mins // 60}시간",
                "action": "block",
                "blockId": "cancel_confirm_block",  # 카카오 블록 ID
                "extra": {
                    "application_id": app_id,
                    "page": page  # 현재 페이지 기억
                }
            })
        
        # 버튼 배열 (이전/다음 페이지)
        buttons = []
        
        if page > 1:
            buttons.append({
                "action": "block",
                "label": f"← 이전 페이지 ({page-1}/{total_pages})",
                "blockId": "cancel_list_block",
                "extra": {"page": page - 1}
            })
        
        if page < total_pages:
            buttons.append({
                "action": "block",
                "label": f"다음 페이지 → ({page+1}/{total_pages})",
                "blockId": "cancel_list_block",
                "extra": {"page": page + 1}
            })
        
        return jsonify(list_card(
            f"신청 내역 ({page}/{total_pages} 페이지)",
            items,
            buttons
        ))
    
    except Exception as e:
        current_app.logger.error(f"Applications list error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/cancel', methods=['POST'])
def cancel_application():
    """
    신청 취소 실행
    
    카카오톡: ListCard의 item 클릭
    
    핵심 로직:
        1. application_id로 신청 정보 조회
        2. 신청 삭제
        3. current_count -1
        4. 트랜잭션 커밋
    
    Returns:
        JSON: 카카오톡 응답
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    params = data.get('action', {}).get('params', {})
    application_id = params.get('application_id')
    return_page = params.get('page', 1)
    
    if not application_id:
        return jsonify(simple_text("잘못된 요청입니다."))
    
    log_api_call(current_app, '/cancel', user_id, {'application_id': application_id})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 신청 정보 조회
        cursor.execute("""
            SELECT a.schedule_id, s.schedule_datetime, s.current_count
            FROM applications a
            JOIN schedules s ON a.schedule_id = s.id
            WHERE a.id = %s AND a.user_id = %s
        """, (application_id, user_id))
        
        result = cursor.fetchone()
        
        if not result:
            conn.rollback()
            return jsonify(simple_text("신청 내역을 찾을 수 없습니다."))
        
        schedule_id, schedule_dt, current_count = result
        
        # 신청 삭제
        cursor.execute("DELETE FROM applications WHERE id = %s", (application_id,))
        
        # current_count 감소
        cursor.execute("""
            UPDATE schedules
            SET current_count = current_count - 1
            WHERE id = %s
        """, (schedule_id,))
        
        conn.commit()
        
        current_app.logger.info(
            f"Application canceled: User={user_id}, Application={application_id}"
        )
        
        return jsonify(simple_text(
            f"✅ {format_datetime_short(schedule_dt)} 신청이 취소되었습니다."
        ))
    
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Cancel error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()


@bp.route('/status', methods=['POST'])
def get_status():
    """
    전체 스케줄 현황 조회
    
    카카오톡 발화: "결과", "현황"
    
    Returns:
        JSON: 카카오톡 응답 (텍스트 형식)
    """
    data = request.get_json()
    user_id = data['userRequest']['user']['id']
    
    log_api_call(current_app, '/status', user_id)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT schedule_datetime, duration_minutes, capacity, current_count
            FROM schedules
            ORDER BY schedule_datetime
            LIMIT 10
        """)
        
        schedules = cursor.fetchall()
        
        if not schedules:
            return jsonify(simple_text("등록된 스케줄이 없습니다."))
        
        # 텍스트 응답 생성
        response_text = "📅 스케줄 현황\n\n"
        
        for schedule_dt, duration_mins, capacity, current_count in schedules:
            status_emoji = "🔴" if current_count >= capacity else "🟢"
            response_text += (
                f"{status_emoji} {format_datetime_short(schedule_dt)}\n"
                f"   ⏰ {duration_mins // 60}시간 | "
                f"👥 {current_count}/{capacity}명\n\n"
            )
        
        response_text += "자세한 현황은 웹페이지에서 확인하세요:\n"
        response_text += "https://yourusername.pythonanywhere.com/web/status"
        
        return jsonify(simple_text(response_text))
    
    except Exception as e:
        current_app.logger.error(f"Status error: {str(e)}", exc_info=True)
        return jsonify(simple_text("서버 에러가 발생했습니다.")), 500
    finally:
        cursor.close()
        conn.close()
