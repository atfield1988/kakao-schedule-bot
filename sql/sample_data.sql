-- 샘플 데이터 (테스트 및 개발용)
-- 프로덕션 시작 전 삭제: TRUNCATE TABLE schedules;

USE scheduledb;  -- 본인의 DB 이름으로 변경

-- 1. 테스트 유저 3명
INSERT INTO users (user_id, nickname) VALUES
('test_user_1', '테스터1'),
('test_user_2', '테스터2'),
('test_user_3', '테스터3');

-- 2. 테스트 스케줄 5개 (다양한 정원)
-- 현재 날짜 기준 앞으로 7일간의 스케줄 생성

-- 정원 1명 (동시성 테스트용)
INSERT INTO schedules (schedule_datetime, duration_minutes, capacity, current_count) VALUES
(DATE_ADD(NOW(), INTERVAL 1 DAY) + INTERVAL 11 HOUR, 240, 1, 0);

-- 정원 5명
INSERT INTO schedules (schedule_datetime, duration_minutes, capacity, current_count) VALUES
(DATE_ADD(NOW(), INTERVAL 1 DAY) + INTERVAL 17 HOUR, 240, 5, 0);

-- 정원 8명
INSERT INTO schedules (schedule_datetime, duration_minutes, capacity, current_count) VALUES
(DATE_ADD(NOW(), INTERVAL 2 DAY) + INTERVAL 11 HOUR, 240, 8, 0);

-- 정원 7명
INSERT INTO schedules (schedule_datetime, duration_minutes, capacity, current_count) VALUES
(DATE_ADD(NOW(), INTERVAL 2 DAY) + INTERVAL 17 HOUR, 240, 7, 0);

-- 정원 10명
INSERT INTO schedules (schedule_datetime, duration_minutes, capacity, current_count) VALUES
(DATE_ADD(NOW(), INTERVAL 3 DAY) + INTERVAL 11 HOUR, 240, 10, 0);

-- 3. 테스트 신청 2개 (테스터1, 테스터2가 첫 번째 스케줄 신청)
-- 실제 테스트 시 자동으로 생성되므로 선택적

-- INSERT INTO applications (user_id, schedule_id) VALUES
-- ('test_user_1', 1),
-- ('test_user_2', 2);

-- 샘플 데이터 확인
SELECT 
    '샘플 데이터 삽입 완료' AS status,
    (SELECT COUNT(*) FROM users) AS users,
    (SELECT COUNT(*) FROM schedules) AS schedules,
    (SELECT COUNT(*) FROM applications) AS applications;

-- 스케줄 현황 확인
SELECT 
    id,
    DATE_FORMAT(schedule_datetime, '%Y-%m-%d %H:%i') AS schedule_time,
    duration_minutes / 60 AS duration_hours,
    capacity,
    current_count,
    CASE 
        WHEN current_count >= capacity THEN '마감'
        ELSE '모집중'
    END AS status
FROM schedules
ORDER BY schedule_datetime;
