# Slide ↔ Audio Sync (CLI + Streamlit)

CSV로 지정한 **슬라이드 시작시각**과 **오디오**를 합쳐 **MP4** 영상을 만드는 템플릿입니다.

- `cli/`: 로컬/서버에서 쓰는 **명령줄 스크립트**
- `app/`: **Streamlit 웹 앱** (Streamlit Community Cloud 배포용)

## 빠른 시작 (로컬)
```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt

# Streamlit 앱 실행
streamlit run app/app.py
```

## Streamlit Community Cloud 배포
1. 이 리포를 GitHub에 푸시
2. Streamlit Cloud에서 New app → 리포/브랜치 선택 → **Main file: `app/app.py`**
3. 루트의 `requirements.txt`가 자동 설치됩니다.
4. 필요 시 루트 `packages.txt`에 `ffmpeg` 한 줄을 추가하면 시스템 ffmpeg를 설치합니다.
   - 기본적으로 `imageio-ffmpeg`가 동봉 바이너리를 제공하므로 보통은 불필요합니다.

## CLI 사용
```bash
# 예시 입력 준비
cp sample/slides_timing_sample.csv .
# PPT 슬라이드 이미지는 sample/slides/ 참고 (여기에 PNG/JPG 넣으세요)

python cli/sync_slides_to_audio.py   --audio narration.wav   --csv slides_timing_sample.csv   --images_dir ./sample/slides   --out out.mp4   --size 1920x1080   --fps 30
```

## CSV 포맷
`filename,start_time` (오름차순 권장). 시간 표기는 `hh:mm:ss(.ms)`/`mm:ss`/`초` 모두 지원.

## 라이선스
MIT
