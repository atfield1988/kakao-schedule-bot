"""
사용자 입력 날짜/시간 파싱

카카오 오픈빌더에서 전달받는 엔티티 값:
- date_day: "3일", "27일" (문자 포함)
- time_hour: "11시", "9시" (문자 포함)
- time_minute: "30분", "0분" (문자 포함)
- duration_hour: "4시간", "8시간" (문자 포함)
- week_day: "월요일", "화요일" (문자)

이 모듈은 한글 문자를 제거하고 숫자만 추출합니다.
"""

import re
from datetime import datetime, timedelta


def extract_number(text):
    """
    텍스트에서 숫자만 추출
    
    Args:
        text (str): "3일", "11시", "30분", "4시간" 형식
    
    Returns:
        int: 숫자 부분만 (예: 3, 11, 30, 4)
    
    Example:
        >>> extract_number("3일")
        3
        >>> extract_number("11시")
        11
        >>> extract_number("30분")
        30
        >>> extract_number("4시간")
        4
    
    Raises:
        ValueError: 숫자가 없을 경우
    """
    if text is None:
        raise ValueError("입력값이 None입니다")
    
    # 숫자만 추출 (정규식)
    match = re.search(r'\d+', str(text))
    if match:
        return int(match.group())
    
    raise ValueError(f"숫자를 추출할 수 없습니다: {text}")


def parse_weekday(weekday_str):
    """
    요일 문자열을 요일 인덱스로 변환
    
    Args:
        weekday_str (str): "월요일", "월", "화요일", "화" 등
    
    Returns:
        int: 요일 인덱스 (0=월요일, 1=화요일, ..., 6=일요일)
    
    Example:
        >>> parse_weekday("월요일")
        0
        >>> parse_weekday("금")
        4
    
    Raises:
        ValueError: 인식할 수 없는 요일
    """
    weekday_map = {
        '월': 0, '월요일': 0,
        '화': 1, '화요일': 1,
        '수': 2, '수요일': 2,
        '목': 3, '목요일': 3,
        '금': 4, '금요일': 4,
        '토': 5, '토요일': 5,
        '일': 6, '일요일': 6,
    }
    
    if weekday_str in weekday_map:
        return weekday_map[weekday_str]
    
    raise ValueError(f"인식할 수 없는 요일: {weekday_str}")


def parse_user_input(day, hour, minute=None):
    """
    사용자 입력 날짜/시간 파싱 (범위 검색용)
    
    카카오 엔티티에서 받은 값을 파싱하여 범위 검색 가능한 형식으로 변환
    
    Args:
        day (str): 날짜 (예: "3일", "27일", "3", "27")
        hour (str): 시간 (예: "11시", "9시", "11", "9")
        minute (str, optional): 분 (예: "30분", "0분", "30", "0")
    
    Returns:
        tuple: (start_datetime, end_datetime)
            - start_datetime: YYYY-MM-DD HH:MM:SS
            - end_datetime: YYYY-MM-DD HH:MM:SS
        
        범위: start ~ end (1시간 범위, 예: 9:00:00 ~ 9:59:59)
    
    Example:
        >>> parse_user_input("27일", "11시")
        (datetime(2025, 11, 27, 11, 0, 0), datetime(2025, 11, 27, 11, 59, 59))
        
        >>> parse_user_input("3", "18")
        (datetime(2025, 12, 3, 18, 0, 0), datetime(2025, 12, 3, 18, 59, 59))
    
    Raises:
        ValueError: 날짜/시간 형식이 잘못된 경우
    """
    try:
        # 1. 숫자 추출 (한글 제거)
        day_num = extract_number(day)
        hour_num = extract_number(hour)
        minute_num = extract_number(minute) if minute else 0
        
        # 2. 유효성 검사
        if not (1 <= day_num <= 31):
            raise ValueError(f"잘못된 날짜: {day_num}일")
        if not (0 <= hour_num <= 23):
            raise ValueError(f"잘못된 시간: {hour_num}시")
        if not (0 <= minute_num <= 59):
            raise ValueError(f"잘못된 분: {minute_num}분")
        
        # 3. 오늘 기준 날짜 계산
        today = datetime.now()
        
        # 오늘 날짜보다 작거나 같으면 이번 달, 크면 다음 달
        if today.day <= day_num:
            target_date = datetime(today.year, today.month, day_num, hour_num, minute_num, 0)
        else:
            # 다음 달
            if today.month == 12:
                target_date = datetime(today.year + 1, 1, day_num, hour_num, minute_num, 0)
            else:
                target_date = datetime(today.year, today.month + 1, day_num, hour_num, minute_num, 0)
        
        # 4. 범위 반환 (1시간 범위: 9시 0분 0초 ~ 9시 59분 59초)
        start_dt = target_date
        end_dt = target_date + timedelta(hours=1) - timedelta(seconds=1)
        
        return (start_dt, end_dt)
    
    except Exception as e:
        raise ValueError(f"날짜 파싱 실패: {str(e)}")


def parse_admin_schedule(day, hour, minute, duration, capacity):
    """
    관리자가 입력한 스케줄 파싱
    
    Args:
        day (str): "27일" 또는 "27"
        hour (str): "11시" 또는 "11"
        minute (str): "0분" 또는 "0"
        duration (str): "4시간" 또는 "4"
        capacity (str): "4명" 또는 "4"
    
    Returns:
        dict: {
            'schedule_datetime': datetime,
            'duration_minutes': int,
            'capacity': int
        }
    
    Example:
        >>> parse_admin_schedule("27일", "11시", "0분", "4시간", "5명")
        {
            'schedule_datetime': datetime(2025, 11, 27, 11, 0, 0),
            'duration_minutes': 240,
            'capacity': 5
        }
    """
    try:
        # 숫자 추출 (한글 제거)
        day_num = extract_number(day)
        hour_num = extract_number(hour)
        minute_num = extract_number(minute) if minute else 0
        duration_hours = extract_number(duration)
        capacity_num = extract_number(capacity)
        
        # 날짜 계산
        today = datetime.now()
        if today.day <= day_num:
            schedule_dt = datetime(today.year, today.month, day_num, hour_num, minute_num, 0)
        else:
            if today.month == 12:
                schedule_dt = datetime(today.year + 1, 1, day_num, hour_num, minute_num, 0)
            else:
                schedule_dt = datetime(today.year, today.month + 1, day_num, hour_num, minute_num, 0)
        
        return {
            'schedule_datetime': schedule_dt,
            'duration_minutes': duration_hours * 60,
            'capacity': capacity_num
        }
    except Exception as e:
        raise ValueError(f"스케줄 파싱 실패: {str(e)}")


def format_datetime_short(dt):
    """
    날짜/시간을 짧은 형식으로 포맷
    
    Example:
        >>> format_datetime_short(datetime(2025, 11, 27, 11, 0, 0))
        "11월 27일 (수) 11:00"
    """
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday = weekdays[dt.weekday()]
    return dt.strftime(f"%m월 %d일 ({weekday}) %H:%M")


def format_datetime_korean(dt):
    """
    날짜/시간을 한글로 포맷
    
    Example:
        >>> format_datetime_korean(datetime(2025, 11, 27, 11, 0, 0))
        "2025년 11월 27일 (수) 11:00"
    """
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday = weekdays[dt.weekday()]
    return dt.strftime(f"%Y년 %m월 %d일 ({weekday}) %H:%M")


def format_duration(minutes):
    """
    분 단위 시간을 포맷
    
    Example:
        >>> format_duration(240)
        "4시간"
        >>> format_duration(90)
        "1시간 30분"
    """
    hours = minutes // 60
    mins = minutes % 60
    
    if mins == 0:
        return f"{hours}시간"
    else:
        return f"{hours}시간 {mins}분"
