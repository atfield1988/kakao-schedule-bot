-- 초기 슈퍼 관리자 등록
-- 사용법:
-- 1. PythonAnywhere에서 챗봇에 한 번 말 걸기 (로그에 user_id 기록됨)
-- 2. logs/error.log에서 본인 user_id 확인
-- 3. 아래 'your_kakao_user_id'를 실제 값으로 변경 후 실행

USE yourusername$scheduledb;  -- 본인의 DB 이름으로 변경

-- 1. 유저 등록
INSERT INTO users (user_id, nickname) 
VALUES ('your_kakao_user_id', '슈퍼관리자');

-- 2. 슈퍼 관리자 권한 부여
-- added_by='system'으로 설정하여 슈퍼 관리자 표시
INSERT INTO admins (user_id, added_by) 
VALUES ('your_kakao_user_id', 'system');

-- 3. 확인
SELECT 
    u.nickname,
    a.added_by,
    a.added_at,
    CASE 
        WHEN a.added_by = 'system' THEN '슈퍼 관리자'
        ELSE '일반 관리자'
    END AS admin_type
FROM admins a
JOIN users u ON a.user_id = u.user_id
WHERE a.user_id = 'your_kakao_user_id';
