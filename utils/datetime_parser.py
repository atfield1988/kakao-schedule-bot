"""
날짜/시간 파싱 및 범위 검색 로직

이 모듈은 카카오톡 엔티티 값을 Python datetime 객체로 변환하고,
'9시' 입력 → 9:00~9:59 범위 검색을 지원합니다.
"""

from datetime import datetime, timedelta
import re


def parse_user_input(day, hour, minute=0):
    """
    유저 입력 파싱 (현재 월 기준 자동 계산)
    
    Args:
        day (str or int): 일 (예: "27" or 27)
        hour (str or int): 시 (예: "11" or 11)
        minute (str or int, optional): 분 (기본 0)
    
    Returns:
        tuple: (start_datetime, end_datetime) 범위 검색용
        None: 잘못된 날짜일 경우
    
    Example:
        >>> parse_user_input("27", "11")
        (datetime(2025, 11, 27, 11, 0, 0), datetime(2025, 11, 27, 12, 0, 0))
        
        >>> parse_user_input("27", "11", "30")
        (datetime(2025, 11, 27, 11, 30, 0), datetime(2025, 11, 27, 12, 30, 0))
    
    Note:
        - 과거 날짜 입력 시 자동으로 다음 달로 추정
        - 범위 끝 = 시작 + 1시간 (9시 → 9:00~9:59:59)
    """
    day = int(day)
    hour = int(hour)
    minute = int(minute)
    
    # 현재 날짜 기준
    now = datetime.now()
    year = now.year
    month = now.month
    
    try:
        # datetime 생성
        start_datetime = datetime(year, month, day, hour, minute, 0)
    except ValueError:
        # 잘못된 날짜 (예: 2월 30일)
        return None
    
    # 과거 날짜면 다음 달로 추정
    if start_datetime < now:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        
        try:
            start_datetime = datetime(year, month, day, hour, minute, 0)
        except ValueError:
            return None
    
    # 범위 끝: 시작 + 1시간
    end_datetime = start_datetime + timedelta(hours=1)
    
    return (start_datetime, end_datetime)


def parse_admin_schedule(day, day_of_week, hour, minute, duration_hours, capacity):
    """
    관리자 스케줄 등록 파싱
    
    Args:
        day (str or int): 일
        day_of_week (str): 요일 (월, 화, 수, 목, 금, 토, 일)
        hour (str or int): 시
        minute (str or int): 분 (기본 0)
        duration_hours (str or int): 근무시간
        capacity (str or int): 정원
    
    Returns:
        dict: {
            'schedule_datetime': datetime 객체,
            'duration_minutes': int,
            'capacity': int
        }
        None: 파싱 실패 시
    
    Example:
        >>> parse_admin_schedule("27", "월", "11", "0", "4", "4")
        {
            'schedule_datetime': datetime(2025, 11, 27, 11, 0, 0),
            'duration_minutes': 240,
            'capacity': 4
        }
    """
    day = int(day)
    hour = int(hour)
    minute = int(minute) if minute else 0
    duration_hours = int(duration_hours)
    capacity = int(capacity)
    
    # 현재 날짜 기준
    now = datetime.now()
    year = now.year
    month = now.month
    
    try:
        schedule_datetime = datetime(year, month, day, hour, minute, 0)
    except ValueError:
        return None
    
    # 과거 날짜면 다음 달로 추정
    if schedule_datetime < now:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        
        try:
            schedule_datetime = datetime(year, month, day, hour, minute, 0)
        except ValueError:
            return None
    
    return {
        'schedule_datetime': schedule_datetime,
        'duration_minutes': duration_hours * 60,
        'capacity': capacity
    }


def format_datetime_korean(dt):
    """
    datetime을 한글 형식으로 변환
    
    Args:
        dt (datetime): datetime 객체
    
    Returns:
        str: "11월 27일 월요일 11시" 형식
    
    Example:
        >>> dt = datetime(2025, 11, 27, 11, 0, 0)
        >>> format_datetime_korean(dt)
        "11월 27일 목요일 11시"
    """
    day_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    day_of_week = day_names[dt.weekday()]
    
    if dt.minute == 0:
        return f"{dt.month}월 {dt.day}일 {day_of_week} {dt.hour}시"
    else:
        return f"{dt.month}월 {dt.day}일 {day_of_week} {dt.hour}시 {dt.minute}분"


def format_datetime_short(dt):
    """
    datetime을 짧은 한글 형식으로 변환
    
    Args:
        dt (datetime): datetime 객체
    
    Returns:
        str: "11월 27일 11시" 형식
    """
    if dt.minute == 0:
        return f"{dt.month}월 {dt.day}일 {dt.hour}시"
    else:
        return f"{dt.month}월 {dt.day}일 {dt.hour}시 {dt.minute}분"
