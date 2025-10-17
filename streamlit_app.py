# Streamlit Cloud 배포를 위한 메인 파일
# 이 파일은 app/app.py를 실행합니다

import sys
import os

# app 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# app.py 실행
if __name__ == "__main__":
    import app
