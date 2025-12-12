
# Smart Study Scheduler

개인화 학습 스케줄 자동 생성 AI (파이썬 / Streamlit 데모 프로젝트)
## 설치 방법 (Installation)

```bash
git clone https://github.com/USERNAME/smart-study-scheduler.git
cd smart-study-scheduler

python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
```

## 사용 방법 (Usage)

```bash
streamlit run src/ui_streamlit.py
```

브라우저에서 과목 정보와 요일별 가용 시간을 입력한 뒤,
'스케줄 생성' 버튼을 눌러 결과를 확인할 수 있습니다.

## 프로젝트 구조

- src/models.py : 데이터 모델 정의
- src/scheduler.py : 스케줄링 알고리즘
- src/storage.py : 설정 저장/불러오기(JSON)
- src/ui_streamlit.py : Streamlit 웹 UI
- tests/test_scheduler.py : pytest 테스트
- .github/workflows/ci.yml : GitHub Actions CI
- requirements.txt : 의존성 패키지 목록
- LICENSE : MIT License
