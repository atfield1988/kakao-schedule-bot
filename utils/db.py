"""
MySQL Connection Pool 관리

이 모듈은 PythonAnywhere 환경에서 MySQL 연결 풀을 생성하고,
연결 풀 부족 시 대기+재시도 로직을 제공합니다.
"""

import time
import mysql.connector
from mysql.connector import pooling
from mysql.connector.errors import PoolError
import os


def create_connection_pool():
    """
    MySQL Connection Pool 생성
    
    Returns:
        MySQLConnectionPool: mysql-connector-python 연결 풀 객체
    
    Raises:
        mysql.connector.Error: DB 연결 실패 시
    
    Note:
        - pool_size=10: 최대 10개 동시 연결 허용
        - pool_reset_session=True: 연결 재사용 시 세션 초기화
        - autocommit=False: 트랜잭션 명시적 제어
    """
    try:
        pool = pooling.MySQLConnectionPool(
            pool_name="schedule_pool",
            pool_size=3,  # 3명 동시 접속 대응
            pool_reset_session=True,
            host=os.environ.get('DB_HOST', 'localhost'),
            port=int(os.environ.get('DB_PORT', 3306)),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', ''),
            database=os.environ.get('DB_NAME', 'scheduledb'),
            autocommit=False,  # 트랜잭션 수동 제어
            get_warnings=True,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        return pool
    except mysql.connector.Error as err:
        print(f"❌ MySQL Connection Pool 생성 실패: {err}")
        raise


# 글로벌 연결 풀 객체 (app.py에서 초기화)
connection_pool = None


def get_db_connection(max_retries=3, retry_delay=0.1):
    """
    Connection Pool에서 연결 가져오기 (대기+재시도 로직)
    
    Args:
        max_retries (int): 최대 재시도 횟수 (기본 3회)
        retry_delay (float): 재시도 대기 시간(초) (기본 0.1초)
    
    Returns:
        mysql.connector.connection.MySQLConnection: DB 연결 객체
    
    Raises:
        PoolError: 재시도 후에도 연결 풀 부족 시
    
    Example:
        >>> conn = get_db_connection()
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT * FROM schedules")
        >>> conn.close()
    
    Note:
        - 연결 풀이 꽉 찼을 때 대기 후 재시도
        - 최대 0.3초(0.1초 × 3회) 대기
        - 이후 PoolError 발생
    """
    if connection_pool is None:
        raise RuntimeError("Connection pool not initialized. Call create_connection_pool() first.")
    
    for attempt in range(max_retries):
        try:
            return connection_pool.get_connection()
        except PoolError as e:
            if attempt < max_retries - 1:
                # 연결 풀 부족, 대기 후 재시도
                time.sleep(retry_delay)
            else:
                # 최대 재시도 횟수 초과
                raise PoolError(
                    f"Connection pool exhausted after {max_retries} retries. "
                    f"Error: {str(e)}"
                )
