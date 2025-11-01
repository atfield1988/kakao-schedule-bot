"""
데이터 검증 로직

이 모듈은 스케줄 인원 변경 시 검증 등
비즈니스 로직 검증을 수행합니다.
"""


def validate_capacity_change(current_count, new_capacity):
    """
    정원 변경 검증
    
    현재 신청자 수보다 적게 정원을 줄일 수 없습니다.
    
    Args:
        current_count (int): 현재 신청자 수
        new_capacity (int): 새로운 정원
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    
    Example:
        >>> validate_capacity_change(3, 5)
        (True, None)
        
        >>> validate_capacity_change(3, 2)
        (False, "현재 신청 인원(3명)보다 적게 설정할 수 없습니다.")
    """
    if new_capacity < current_count:
        return (
            False,
            f"현재 신청 인원({current_count}명)보다 적게 설정할 수 없습니다. "
            f"최소 {current_count}명 이상으로 설정해주세요."
        )
    
    return (True, None)


def validate_datetime_range(start_dt, end_dt):
    """
    날짜 범위 유효성 검증
    
    Args:
        start_dt (datetime): 시작 시간
        end_dt (datetime): 종료 시간
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if start_dt >= end_dt:
        return (False, "시작 시간이 종료 시간보다 늦습니다.")
    
    return (True, None)
