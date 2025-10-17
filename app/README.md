# Streamlit App

브라우저에서 오디오/CSV/이미지 업로드 → MP4 생성까지 수행합니다.

## 로컬 실행
```bash
pip install -r ../requirements.txt
streamlit run app.py
```

## Streamlit Cloud
- 메인 파일: `app/app.py`
- 루트 `requirements.txt`만 설치됩니다.
- 필요 시 루트 `packages.txt`에 `ffmpeg` 추가.
