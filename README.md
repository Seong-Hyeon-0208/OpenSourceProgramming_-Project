
# Smart Study Scheduler

개인화 학습 스케줄 자동 생성 AI (파이썬 / Streamlit 데모 프로젝트)
본 프로젝트는 사용자의 과목 정보, 시험 일정, 가용 시간, 학습 유형을 입력받아  
**주간 학습 시간표를 자동으로 생성하는 웹 애플리케이션**입니다.

---

## 개발 환경

- Python **3.11.x** (권장)
- Streamlit
- pytest
- GitHub Actions (CI)

---

## 설치 방법 (Installation)

```bash
# Python 3.11 이상 권장
# 프로젝트 클론 또는 압축 해제 후
cd OpenSourceProgramming_-Project

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

## 사용 방법 (Usage)

```bash
streamlit run src/ui_streamlit.py
```
실행 후 브라우저에서 다음 기능을 사용할 수 있습니다.
과목 추가 / 삭제
과목별 주당 학습 시간 설정
시험 날짜 입력 (시험 이후 자동 제외)
학습 유형 선택
장기 몰입형 (2~3시간)
분배형 (1~2시간)
요일별 공부 불가능 시간 설정
색 이모지(🟥🟧🟨🟩🟦🟪) 기반 시간표 출력
CSV 다운로드

## 프로젝트 구조

- src/models.py : 데이터 모델 정의
- src/scheduler.py : 스케줄링 알고리즘
- src/storage.py : 설정 저장/불러오기(JSON)
- src/ui_streamlit.py : Streamlit 웹 UI
- tests/test_scheduler.py : pytest 테스트
- .github/workflows/ci.yml : GitHub Actions CI
- requirements.txt : 의존성 패키지 목록
- LICENSE : MIT License
