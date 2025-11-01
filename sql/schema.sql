-- kakao-schedule-bot Database Schema
-- MySQL 5.7+

-- 1. 유저 테이블
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL COMMENT '카카오톡 user_id',
    nickname VARCHAR(255) NOT NULL COMMENT '유저 닉네임 (길이 제한 없음, 중복 허용)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='사용자 정보';

-- 2. 관리자 테이블
CREATE TABLE IF NOT EXISTS admins (
    user_id VARCHAR(100) PRIMARY KEY COMMENT '카카오톡 user_id',
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '관리자 추가 시간',
    added_by VARCHAR(100) COMMENT '추가한 사람 (system = 슈퍼 관리자)',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='관리자 권한';

-- 3. 스케줄 테이블
CREATE TABLE IF NOT EXISTS schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    schedule_datetime DATETIME NOT NULL COMMENT '스케줄 시간 (DATETIME 타입으로 범위 검색 최적화)',
    duration_minutes INT NOT NULL COMMENT '근무 시간(분)',
    capacity INT NOT NULL COMMENT '총 정원',
    current_count INT DEFAULT 0 COMMENT '현재 신청자 수',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 유일성: 같은 시간대에 중복 스케줄 방지
    UNIQUE KEY uq_schedule (schedule_datetime),
    
    -- 범위 검색 최적화 (>= AND < 쿼리)
    INDEX idx_datetime (schedule_datetime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='스케줄 정보';

-- 4. 신청 테이블
CREATE TABLE IF NOT EXISTS applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL COMMENT '신청자 user_id',
    schedule_id INT NOT NULL COMMENT '스케줄 ID',
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '신청 시간',
    
    -- 외래 키 (CASCADE: 스케줄 삭제 시 신청도 자동 삭제)
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
    
    -- 중복 신청 방지 (유저당 스케줄 1개만)
    UNIQUE KEY unique_application (user_id, schedule_id),
    
    -- 인덱스: 취소 목록 조회 최적화
    INDEX idx_user (user_id),
    
    -- 인덱스: 결과 조회 최적화
    INDEX idx_schedule_user (schedule_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='신청 내역';

-- 5. 에러 로그 테이블 (선택적)
CREATE TABLE IF NOT EXISTS error_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    error_type VARCHAR(100) COMMENT '에러 타입',
    error_message TEXT COMMENT '에러 메시지',
    stack_trace TEXT COMMENT '스택 트레이스',
    user_id VARCHAR(100) COMMENT '발생 user_id',
    request_data JSON COMMENT '요청 데이터',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created (created_at),
    INDEX idx_type (error_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='에러 로그 (선택적)';

-- 스키마 정보 확인
SELECT 
    'Schema created successfully' AS status,
    COUNT(*) AS table_count
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('users', 'admins', 'schedules', 'applications', 'error_logs');
