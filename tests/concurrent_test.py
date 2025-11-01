"""
동시성 테스트 스크립트

6개 케이스 x 10회 반복 = 총 60개 테스트
3가지 검증: 응답 일관성, 응답 시간, 에러 발생

실행 방법:
  로컬 테스트: python concurrent_test.py --url http://localhost:5000
  서버 테스트: python concurrent_test.py --url https://yourusername.pythonanywhere.com
"""

import requests
import threading
import time
import json
import argparse
from datetime import datetime, timedelta


class ConcurrentTester:
    """동시성 테스트 실행 및 결과 리포트 생성"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.test_results = []
    
    def create_schedule(self, capacity):
        """
        테스트용 스케줄 생성
        
        Args:
            capacity (int): 정원
        
        Returns:
            int: 생성된 schedule_id
        """
        # 관리자로 스케줄 등록
        tomorrow = datetime.now() + timedelta(days=1)
        day = tomorrow.day
        hour = 11
        
        # 임시로 admin API 호출 (실제로는 DB 직접 INSERT)
        # 여기서는 간단히 DB에 직접 INSERT한다고 가정
        print(f"[SETUP] Creating schedule with capacity={capacity}")
        
        # 실제 구현에서는 MySQL 연결하여 INSERT
        # 여기서는 schedule_id를 반환한다고 가정
        return 1  # 임시 ID
    
    def apply_concurrent(self, schedule_id, user_count):
        """
        동시 신청 실행
        
        Args:
            schedule_id (int): 스케줄 ID
            user_count (int): 동시 신청자 수
        
        Returns:
            dict: {
                'responses': [응답 리스트],
                'status_codes': [상태 코드 리스트],
                'response_times': [응답 시간 리스트]
            }
        """
        responses = []
        status_codes = []
        response_times = []
        lock = threading.Lock()
        
        def apply_single(user_index):
            """단일 유저 신청"""
            user_id = f"test_user_{user_index}"
            
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{self.base_url}/apply",
                    json={
                        "userRequest": {
                            "user": {"id": user_id},
                            "utterance": "27일 11시"
                        },
                        "action": {
                            "params": {
                                "@date_day": "27",
                                "@time_hour": "11"
                            }
                        }
                    },
                    timeout=5
                )
                
                elapsed = time.time() - start_time
                
                with lock:
                    responses.append(response.json())
                    status_codes.append(response.status_code)
                    response_times.append(elapsed)
            
            except Exception as e:
                elapsed = time.time() - start_time
                with lock:
                    responses.append({"error": str(e)})
                    status_codes.append(0)
                    response_times.append(elapsed)
        
        # 쓰레드 생성 및 실행
        threads = []
        for i in range(user_count):
            thread = threading.Thread(target=apply_single, args=(i,))
            threads.append(thread)
        
        # 동시 시작
        for thread in threads:
            thread.start()
        
        # 모든 쓰레드 종료 대기
        for thread in threads:
            thread.join()
        
        return {
            'responses': responses,
            'status_codes': status_codes,
            'response_times': response_times
        }
    
    def verify_db_count(self, schedule_id, expected_count):
        """
        DB에 실제로 저장된 신청 개수 확인
        
        Args:
            schedule_id (int): 스케줄 ID
            expected_count (int): 예상 개수
        
        Returns:
            int: 실제 DB count
        """
        # 실제 구현에서는 MySQL 연결하여 SELECT COUNT(*)
        # 여기서는 GET /status API로 확인한다고 가정
        
        try:
            response = requests.get(f"{self.base_url}/api/schedule/{schedule_id}")
            data = response.json()
            return data.get('current_count', 0)
        except:
            return -1  # 조회 실패
    
    def run_test_case(self, case_id, capacity, concurrent_users, iterations=10):
        """
        단일 테스트 케이스 실행 (10회 반복)
        
        Args:
            case_id (int): 케이스 번호
            capacity (int): 정원
            concurrent_users (int): 동시 신청자 수
            iterations (int): 반복 횟수
        
        Returns:
            dict: 테스트 결과
        """
        print(f"\n{'='*60}")
        print(f"Test Case {case_id}: Capacity={capacity}, Users={concurrent_users}")
        print(f"{'='*60}")
        
        case_results = []
        
        for iteration in range(1, iterations + 1):
            print(f"\n[Iteration {iteration}/{iterations}]")
            
            # 1. 스케줄 생성
            schedule_id = self.create_schedule(capacity)
            
            # 2. 동시 신청
            result = self.apply_concurrent(schedule_id, concurrent_users)
            
            # 3. DB 확인
            db_count = self.verify_db_count(schedule_id, capacity)
            
            # 4. 검증
            verification = self.verify_results(
                result, 
                capacity, 
                concurrent_users, 
                db_count
            )
            
            # 5. 결과 저장
            case_results.append({
                'iteration': iteration,
                'schedule_id': schedule_id,
                'responses': result['responses'],
                'status_codes': result['status_codes'],
                'response_times': result['response_times'],
                'db_count': db_count,
                'verification': verification,
                'status': 'PASS' if verification['all_passed'] else 'FAIL'
            })
            
            # 결과 출력
            self.print_iteration_result(iteration, verification, db_count)
            
            # 다음 반복 전 대기
            if iteration < iterations:
                time.sleep(0.5)
        
        # 전체 통과율 계산
        pass_count = sum(1 for r in case_results if r['status'] == 'PASS')
        
        return {
            'case_id': case_id,
            'capacity': capacity,
            'concurrent_users': concurrent_users,
            'iterations': iterations,
            'results': case_results,
            'summary': {
                'pass_count': pass_count,
                'fail_count': iterations - pass_count,
                'pass_rate': f"{pass_count}/{iterations}",
                'overall_status': '✅ SUCCESS' if pass_count == iterations else '❌ FAILED'
            }
        }
    
    def verify_results(self, result, capacity, concurrent_users, db_count):
        """
        3가지 검증
        
        1. 응답 일관성: 성공 개수 = capacity
        2. 응답 시간: 모든 응답 < 1초
        3. 에러 발생: 500 에러 = 0개
        
        Returns:
            dict: 검증 결과
        """
        responses = result['responses']
        status_codes = result['status_codes']
        response_times = result['response_times']
        
        # 검증 1: 응답 일관성
        success_count = sum(
            1 for r in responses 
            if '신청이 완료되었습니다' in str(r)
        )
        fail_count = sum(
            1 for r in responses 
            if '정원이 마감되었습니다' in str(r)
        )
        
        consistency_pass = (success_count == capacity) and (db_count == capacity)
        
        # 검증 2: 응답 시간
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        time_pass = max_response_time < 1.0
        
        # 검증 3: 에러 발생
        error_count = sum(1 for code in status_codes if code >= 500)
        
        error_pass = error_count == 0
        
        all_passed = consistency_pass and time_pass and error_pass
        
        return {
            'consistency': {
                'pass': consistency_pass,
                'success_count': success_count,
                'fail_count': fail_count,
                'expected': capacity
            },
            'response_time': {
                'pass': time_pass,
                'avg': round(avg_response_time, 3),
                'max': round(max_response_time, 3),
                'threshold': 1.0
            },
            'errors': {
                'pass': error_pass,
                'error_count': error_count
            },
            'all_passed': all_passed
        }
    
    def print_iteration_result(self, iteration, verification, db_count):
        """반복 결과 출력"""
        print(f"  DB Count: {db_count}")
        print(f"  ✓ Consistency: {'PASS' if verification['consistency']['pass'] else 'FAIL'}")
        print(f"  ✓ Response Time: {'PASS' if verification['response_time']['pass'] else 'FAIL'} "
              f"(avg={verification['response_time']['avg']}s)")
        print(f"  ✓ Errors: {'PASS' if verification['errors']['pass'] else 'FAIL'}")
        print(f"  Status: {'✅ PASS' if verification['all_passed'] else '❌ FAIL'}")
    
    def run_all_tests(self):
        """
        6개 케이스 모두 실행
        
        테스트 케이스:
          TC1: 정원 1명, 동시 10명
          TC2: 정원 5명, 동시 10명
          TC3: 정원 8명, 동시 8명
          TC4: 정원 5명, 동시 7명
          TC5: 정원 7명, 동시 4명
          TC6: 정원 10명, 동시 10명
        """
        test_cases = [
            (1, 1, 10),   # TC1
            (2, 5, 10),   # TC2
            (3, 8, 8),    # TC3
            (4, 5, 7),    # TC4
            (5, 7, 4),    # TC5
            (6, 10, 10),  # TC6
        ]
        
        all_results = []
        
        for case_id, capacity, concurrent_users in test_cases:
            result = self.run_test_case(case_id, capacity, concurrent_users)
            all_results.append(result)
            self.test_results.append(result)
        
        return all_results
    
    def generate_report(self):
        """
        JSON 리포트 생성
        
        파일: test_report.json
        """
        total_tests = sum(r['iterations'] for r in self.test_results)
        passed_tests = sum(r['summary']['pass_count'] for r in self.test_results)
        failed_tests = total_tests - passed_tests
        
        report = {
            'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'base_url': self.base_url,
            'cases': self.test_results,
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'pass_rate': f"{passed_tests}/{total_tests}",
                'overall_status': '✅ ALL PASS' if failed_tests == 0 else f'❌ {failed_tests} FAILED'
            }
        }
        
        # JSON 파일 저장
        with open('test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print("TEST REPORT GENERATED: test_report.json")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Status: {report['summary']['overall_status']}")
        print(f"{'='*60}\n")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='동시성 테스트 스크립트')
    parser.add_argument('--url', required=True, help='서버 URL (예: http://localhost:5000)')
    args = parser.parse_args()
    
    print("="*60)
    print("CONCURRENT TEST STARTING")
    print("="*60)
    print(f"Target URL: {args.url}")
    print(f"Test Cases: 6")
    print(f"Iterations per case: 10")
    print(f"Total tests: 60")
    print("="*60)
    
    # 테스터 초기화
    tester = ConcurrentTester(args.url)
    
    # 모든 테스트 실행
    try:
        tester.run_all_tests()
        tester.generate_report()
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
    except Exception as e:
        print(f"\n\n테스트 에러: {str(e)}")


if __name__ == '__main__':
    main()
