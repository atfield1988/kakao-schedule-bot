"""
데이터베이스 모델 (참고용)

실제로는 raw SQL을 사용하지만, 
스키마 구조를 이해하기 위한 참고용 모델입니다.
"""

from datetime import datetime


class User:
    """
    사용자 모델
    
    Attributes:
        id (int): 사용자 고유 ID
        user_id (str): 카카오톡 user_id (고유)
        nickname (str): 사용자 닉네임
        created_at (datetime): 생성 시간
    """
    def __init__(self, id, user_id, nickname, created_at):
        self.id = id
        self.user_id = user_id
        self.nickname = nickname
        self.created_at = created_at


class Admin:
    """
    관리자 모델
    
    Attributes:
        user_id (str): 카카오톡 user_id (PK)
        added_at (datetime): 관리자 추가 시간
        added_by (str): 추가한 사람 ('system' = 슈퍼 관리자)
    """
    def __init__(self, user_id, added_at, added_by):
        self.user_id = user_id
        self.added_at = added_at
        self.added_by = added_by


class Schedule:
    """
    스케줄 모델
    
    Attributes:
        id (int): 스케줄 고유 ID
        schedule_datetime (datetime): 스케줄 시간
        duration_minutes (int): 근무 시간(분)
        capacity (int): 총 정원
        current_count (int): 현재 신청자 수
        created_at (datetime): 생성 시간
    """
    def __init__(self, id, schedule_datetime, duration_minutes, 
                 capacity, current_count, created_at):
        self.id = id
        self.schedule_datetime = schedule_datetime
        self.duration_minutes = duration_minutes
        self.capacity = capacity
        self.current_count = current_count
        self.created_at = created_at


class Application:
    """
    신청 모델
    
    Attributes:
        id (int): 신청 고유 ID
        user_id (str): 신청자 user_id
        schedule_id (int): 스케줄 ID
        applied_at (datetime): 신청 시간
    """
    def __init__(self, id, user_id, schedule_id, applied_at):
        self.id = id
        self.user_id = user_id
        self.schedule_id = schedule_id
        self.applied_at = applied_at


class ErrorLog:
    """
    에러 로그 모델 (선택적)
    
    Attributes:
        id (int): 로그 ID
        error_type (str): 에러 타입
        error_message (str): 에러 메시지
        stack_trace (str): 스택 트레이스
        user_id (str): 발생 user_id
        created_at (datetime): 발생 시간
    """
    def __init__(self, id, error_type, error_message, 
                 stack_trace, user_id, created_at):
        self.id = id
        self.error_type = error_type
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.user_id = user_id
        self.created_at = created_at
