"""
관리자 인증 로직

이 모듈은 일반 관리자와 슈퍼 관리자를 구분하여 인증합니다.
"""

from utils.db import get_db_connection


def is_admin(user_id):
    """
    관리자 여부 확인 (일반 관리자 + 슈퍼 관리자)
    
    Args:
        user_id (str): 카카오톡 user_id
    
    Returns:
        bool: 관리자면 True, 아니면 False
    
    Example:
        >>> is_admin("user123")
        True
        
        >>> is_admin("normal_user")
        False
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT 1 FROM admins WHERE user_id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        return bool(result)
    finally:
        cursor.close()
        conn.close()


def is_super_admin(user_id):
    """
    슈퍼 관리자 여부 확인
    
    슈퍼 관리자는 added_by='system'인 관리자입니다.
    초기 SQL로 등록된 관리자만 슈퍼 관리자 권한을 가집니다.
    
    Args:
        user_id (str): 카카오톡 user_id
    
    Returns:
        bool: 슈퍼 관리자면 True, 아니면 False
    
    Example:
        >>> is_super_admin("super_admin_id")
        True
        
        >>> is_super_admin("normal_admin_id")
        False
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT added_by FROM admins WHERE user_id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return False
        
        # added_by가 'system'인 경우만 슈퍼 관리자
        return result[0] == 'system'
    finally:
        cursor.close()
        conn.close()


def get_admin_info(user_id):
    """
    관리자 정보 조회
    
    Args:
        user_id (str): 카카오톡 user_id
    
    Returns:
        dict: {
            'is_admin': bool,
            'is_super_admin': bool,
            'nickname': str or None,
            'added_at': datetime or None
        }
        None: 관리자가 아닌 경우
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT u.nickname, a.added_by, a.added_at
            FROM admins a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if not result:
            return None
        
        nickname, added_by, added_at = result
        
        return {
            'is_admin': True,
            'is_super_admin': (added_by == 'system'),
            'nickname': nickname,
            'added_at': added_at
        }
    finally:
        cursor.close()
        conn.close()
