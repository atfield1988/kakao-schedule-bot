# 카카오톡 스케줄 관리 챗봇

선착순 신청 기능을 갖춘 스케줄 관리 챗봇입니다.

## 🎯 주요 기능

- ✅ **선착순 신청**: 10명 동시 신청 → 1명만 성공 (정원 1명 기준)
- ✅ **범위 검색**: "9시" 입력 → 9시 00분~59분 스케줄 자동 매칭
- ✅ **페이지네이션**: 신청 내역 5개씩 표시 (이전/다음 버튼)
- ✅ **관리자 추가**: 슈퍼 관리자가 챗봇에서 다른 관리자 추가/삭제
- ✅ **시간 변경**: 컨텍스트 2단계로 스케줄 시간 변경
- ✅ **인원 변경**: 현재 신청자보다 적게 줄일 수 없도록 검증
- ✅ **웹 현황**: 색상 코딩(마감/미달)으로 스케줄 현황 표시

---

## 📋 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [로컬 개발 환경 설정](#로컬-개발-환경-설정)
3. [PythonAnywhere 배포](#pythonanywhere-배포)
4. [카카오 오픈빌더 연동](#카카오-오픈빌더-연동)
5. [테스트 실행](#테스트-실행)
6. [트러블슈팅](#트러블슈팅)

---

## 🔧 시스템 요구사항

### 필수 소프트웨어
- Python 3.8 이상
- MySQL 5.7 이상
- Git

### 필수 계정
- PythonAnywhere 무료 계정
- 카카오 디벨로퍼 계정
- 카카오톡 채널

---

## 🚀 로컬 개발 환경 설정

### 1. 프로젝트 클론

\`\`\`bash
git clone https://github.com/yourusername/kakao-schedule-bot.git
cd kakao-schedule-bot
\`\`\`

### 2. 가상환경 생성

**Windows:**
\`\`\`bash
python -m venv venv
venv\\Scripts\\activate
\`\`\`

**Mac/Linux:**
\`\`\`bash
python3 -m venv venv
source venv/bin/activate
\`\`\`

### 3. 의존성 설치

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 4. 환경 변수 설정

\`\`\`bash
cp .env.example .env
\`\`\`

`.env` 파일 편집:
\`\`\`env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=scheduledb
FLASK_ENV=development
SECRET_KEY=생성필요
\`\`\`

**SECRET_KEY 생성:**
\`\`\`python
python -c "import secrets; print(secrets.token_hex(32))"
\`\`\`

### 5. MySQL DB 생성

\`\`\`sql
CREATE DATABASE scheduledb CHARACTER SET utf8mb4;
USE scheduledb;
SOURCE sql/schema.sql;
SOURCE sql/sample_data.sql;
\`\`\`

### 6. 로컬 서버 실행

\`\`\`bash
python app.py
\`\`\`

**확인:** http://localhost:5000/health

---

## 🌐 PythonAnywhere 배포

### 1. 계정 생성

https://www.pythonanywhere.com 가입

### 2. MySQL 설정

1. Databases 메뉴
2. Initialize MySQL (비밀번호 설정 - 반드시 기록!)
3. DB 생성: `yourusername$scheduledb`

### 3. 스키마 실행

MySQL 콘솔에서:
\`\`\`sql
USE yourusername$scheduledb;
-- schema.sql 내용 복사-붙여넣기
-- sample_data.sql 내용 복사-붙여넣기
\`\`\`

### 4. 코드 업로드

Bash 콘솔에서:
\`\`\`bash
cd ~
git clone https://github.com/yourusername/kakao-schedule-bot.git
cd kakao-schedule-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

### 5. 웹 앱 생성

1. Web 메뉴 → Add a new web app
2. Manual configuration → Python 3.10
3. WSGI 파일 편집:

\`\`\`python
import sys
import os

path = '/home/yourusername/kakao-schedule-bot'
sys.path.insert(0, path)

# 환경 변수 설정
os.environ['DB_HOST'] = 'yourusername.mysql.pythonanywhere-services.com'
os.environ['DB_USER'] = 'yourusername'
os.environ['DB_PASSWORD'] = 'your_mysql_password'
os.environ['DB_NAME'] = 'yourusername$scheduledb'
os.environ['SECRET_KEY'] = 'your-secret-key'
os.environ['FLASK_ENV'] = 'production'

from app import app as application
\`\`\`

4. Virtualenv 경로: `/home/yourusername/kakao-schedule-bot/venv`
5. Reload 버튼 클릭

### 6. 슈퍼 관리자 등록

**1단계: user_id 확인**

챗봇에게 아무 메시지 전송 → Bash 콘솔:
\`\`\`bash
tail -f ~/kakao-schedule-bot/logs/app.log
# User ID: 158603 확인
\`\`\`

**2단계: SQL 실행**

\`\`\`sql
USE yourusername$scheduledb;

INSERT INTO users (user_id, nickname) 
VALUES ('158603', '슈퍼관리자');

INSERT INTO admins (user_id, added_by) 
VALUES ('158603', 'system');

-- 확인
SELECT * FROM admins;
\`\`\`

---

## 📱 카카오 오픈빌더 연동

### 1. 커스텀 엔티티 생성 (5개)

| 엔티티명 | 패턴 | 예시 |
|----------|------|------|
| `@date_day` | `(\d{1,2})일` | 1일, 27일 |
| `@time_hour` | `(\d{1,2})시` | 9시, 11시 |
| `@time_minute` | `(\d{1,2})분` | 30분 |
| `@duration_hour` | `(\d{1,2})시간` | 4시간 |
| `@capacity_count` | `(\d{1,3})명` | 4명 |

### 2. 블록 생성 (13개)

#### 유저 블록
1. **Welcome**: "안녕" → `/welcome`
2. **Apply**: "@date_day @time_hour" → `/apply`
3. **Cancel List**: "취소" → `/user/applications`
4. **Cancel**: (ListCard item 클릭) → `/cancel`
5. **Status**: "결과" → `/status`

#### 관리자 블록
6. **Register**: "@date_day @time_hour @duration_hour @capacity_count" → `/admin/register`
7. **Modify Select**: "@date_day @time_hour 변경" → `/admin/modify/select`
8. **Modify Execute**: (컨텍스트) → `/admin/modify/execute`
9. **Modify Capacity**: "@date_day @time_hour 인원 @capacity_count" → `/admin/modify/capacity`
10. **Delete**: "@date_day @time_hour 삭제" → `/admin/delete`
11. **Add Admin**: "관리자 추가 ..." → `/admin/add_admin`
12. **Remove Admin**: "관리자 삭제 ..." → `/admin/remove_admin`

---

## 🧪 테스트 실행

### 로컬 테스트

\`\`\`bash
cd tests
python concurrent_test.py --url http://localhost:5000
\`\`\`

### 서버 테스트

\`\`\`bash
python concurrent_test.py --url https://yourusername.pythonanywhere.com
\`\`\`

### 결과 확인

\`\`\`bash
cat test_report.json
\`\`\`

**성공 예시:**
\`\`\`json
{
  "summary": {
    "total_tests": 60,
    "passed": 60,
    "overall_status": "✅ ALL PASS"
  }
}
\`\`\`

---

## 🔧 트러블슈팅

### 문제 1: "database is locked"

**원인**: SQLite 사용 중

**해결**: config.py에서 MySQL 확인

### 문제 2: 동시 신청 실패

**원인**: Connection Pool 미설정

**해결**: utils/db.py에서 `pool_size=10` 확인

### 문제 3: 웹 앱 500 에러

**원인**: WSGI 환경 변수 누락

**해결**: WSGI 파일에서 모든 환경 변수 재확인

---

## 📝 라이센스

MIT License

---

## 📧 문의

GitHub Issues: https://github.com/yourusername/kakao-schedule-bot/issues
