import streamlit as st
import pandas as pd
import tempfile, os, io, re, gc
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Slide↔Audio Sync to MP4", layout="centered")
st.title("🎬 Slide ↔ Audio 타이밍 싱크 → MP4")
st.caption("CSV(슬라이드 파일명, 시작시각) + 오디오를 업로드하면 자동으로 MP4를 생성합니다.")

# 사용 안내
with st.expander("📋 사용 방법", expanded=False):
    st.markdown("""
    **1. 파일 준비**
    - 오디오 파일: MP3, WAV, M4A, AAC 형식 (최대 100MB)
    - CSV 파일: `filename,start_time` 컬럼 포함
    - 이미지 파일: PNG, JPG 형식 (최대 50개)
    
    **2. CSV 형식 예시**
    ```
    filename,start_time
    slide1.png,0:00
    slide2.png,0:30
    slide3.png,1:15
    ```
    
    **3. 시간 형식**
    - `0:30` (분:초)
    - `1:15:30` (시:분:초)
    - `90` (초)
    
    **4. 주의사항**
    - 이미지 파일명이 CSV의 filename과 정확히 일치해야 합니다
    - start_time은 오름차순으로 정렬되어야 합니다
    - 처리 시간은 파일 크기에 따라 달라집니다
    """)

# 파일 크기 제한 안내
st.info("💡 **파일 제한**: 오디오 최대 100MB, 이미지 최대 50개")

def parse_size(size_str: str):
    m = re.match(r'^(\d+)x(\d+)$', size_str.strip())
    if not m:
        raise ValueError("--size 형식이 잘못되었습니다. 예: 1920x1080")
    return int(m.group(1)), int(m.group(2))

def parse_time_to_seconds(t: str) -> float:
    s = str(t).strip()
    if re.match(r'^\d+(\.\d+)?$', s):
        return float(s)
    parts = s.split(':')
    parts = [p.strip() for p in parts]
    if len(parts) == 3:
        h, m, sec = parts
        return int(h)*3600 + int(m)*60 + float(sec)
    elif len(parts) == 2:
        m, sec = parts
        return int(m)*60 + float(sec)
    elif len(parts) == 1:
        return float(parts[0])
    else:
        raise ValueError(f"시간 파싱 실패: {t}")

def fit_image_clip(path: str, duration: float, target_w: int, target_h: int) -> ImageClip:
    """이미지를 지정된 크기에 맞춰 ImageClip 생성"""
    try:
        clip = ImageClip(path, duration=duration)
        w, h = clip.size
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        clip = clip.resize(newsize=(new_w, new_h)).on_color(
            size=(target_w, target_h),
            color=(0,0,0),
            col_opacity=1.0,
            pos=("center","center")
        )
        return clip
    except Exception as e:
        logger.error(f"이미지 클립 생성 실패: {path}, 오류: {e}")
        raise

st.subheader("1) 파일 업로드")
audio_file = st.file_uploader("오디오 파일 (mp3/wav 등)", type=["mp3","wav","m4a","aac"])
csv_file = st.file_uploader("CSV (filename,start_time)", type=["csv"])
images = st.file_uploader("슬라이드 이미지들 (PNG/JPG 여러 개 선택)", type=["png","jpg","jpeg"], accept_multiple_files=True)

st.subheader("2) 옵션")
col1, col2 = st.columns(2)
with col1:
    size_str = st.text_input("출력 해상도 (WxH)", value="1920x1080")
with col2:
    fps = st.number_input("FPS", value=30, min_value=1, max_value=120, step=1)
end_padding = st.number_input("오디오 끝 이후 여유(초)", value=0.0, min_value=0.0, step=0.1)

process_btn = st.button("MP4 생성")

if process_btn:
    if not (audio_file and csv_file and images):
        st.error("오디오, CSV, 이미지 파일을 모두 업로드해 주세요.")
        st.stop()
    
    # 파일 크기 검증
    if audio_file.size > 100 * 1024 * 1024:  # 100MB
        st.error("오디오 파일이 너무 큽니다. 100MB 이하로 업로드해 주세요.")
        st.stop()
    
    if len(images) > 50:
        st.error("이미지 파일이 너무 많습니다. 50개 이하로 업로드해 주세요.")
        st.stop()

    try:
        with tempfile.TemporaryDirectory() as workdir:
            logger.info(f"작업 디렉토리: {workdir}")
            
            # 오디오 파일 저장
            audio_path = os.path.join(workdir, audio_file.name)
            with open(audio_path, "wb") as f:
                f.write(audio_file.read())
            logger.info(f"오디오 파일 저장 완료: {audio_file.name}")

            # 이미지 파일들 저장
            images_dir = os.path.join(workdir, "slides")
            os.makedirs(images_dir, exist_ok=True)
            img_name_to_path = {}
            for up in images:
                ipath = os.path.join(images_dir, up.name)
                with open(ipath, "wb") as f:
                    f.write(up.read())
                img_name_to_path[up.name] = ipath
            logger.info(f"이미지 파일 {len(images)}개 저장 완료")

            # CSV 파일 처리
            df = pd.read_csv(csv_file)
            if 'filename' not in df.columns or 'start_time' not in df.columns:
                st.error("CSV에는 'filename','start_time' 컬럼이 필요합니다.")
                st.stop()

            try:
                df['start_sec'] = df['start_time'].apply(parse_time_to_seconds)
            except Exception as e:
                st.error(f"시간 파싱 오류: {e}")
                st.stop()

            df = df.sort_values('start_sec', ascending=True).reset_index(drop=True)
            if not df['start_sec'].is_monotonic_increasing:
                st.error("start_time(초)이 오름차순이어야 합니다.")
                st.stop()

            # 이미지 파일 존재 확인
            missing_files = [fn for fn in df['filename'] if fn not in img_name_to_path]
            if missing_files:
                st.error(f"이미지 파일이 업로드되지 않았습니다: {', '.join(missing_files)}")
                st.stop()

            try:
                target_w, target_h = parse_size(size_str)
            except Exception as e:
                st.error(f"해상도 파싱 오류: {e}")
                st.stop()

            # 오디오 로드
            st.info("오디오 파일 로드 중...")
            try:
                audio = AudioFileClip(audio_path)
                audio_duration = float(audio.duration)
                logger.info(f"오디오 길이: {audio_duration:.2f}초")
            except Exception as e:
                st.error(f"오디오 파일 로드 실패: {e}")
                st.stop()

            # 슬라이드 지속시간 계산
            starts = df['start_sec'].tolist()
            durations = []
            for i, s in enumerate(starts):
                if i < len(starts) - 1:
                    d = max(0.01, starts[i+1] - s)
                else:
                    d = max(0.01, audio_duration - s + float(end_padding))
                durations.append(d)

            # 이미지 클립 생성
            clips = []
            prog = st.progress(0.0, text="이미지 렌더링 중...")
            for i, (fn, dur) in enumerate(zip(df['filename'], durations)):
                try:
                    clip = fit_image_clip(img_name_to_path[fn], dur, target_w, target_h)
                    clips.append(clip)
                    prog.progress((i+1)/len(durations))
                except Exception as e:
                    st.error(f"이미지 처리 실패 ({fn}): {e}")
                    st.stop()
            
            # 비디오 합치기
            st.info("비디오 합치는 중...")
            try:
                video = concatenate_videoclips(clips, method="compose")
                final_duration = max(video.duration, audio_duration + float(end_padding))
                video = video.set_duration(final_duration).set_audio(audio.set_duration(final_duration))
            except Exception as e:
                st.error(f"비디오 합치기 실패: {e}")
                st.stop()

            # MP4 파일 생성
            out_path = os.path.join(workdir, "out.mp4")
            st.info("MP4 파일 생성 중...")
            try:
                video.write_videofile(
                    out_path,
                    fps=int(fps),
                    codec="libx264",
                    audio_codec="aac",
                    threads=2,
                    preset="medium",
                    ffmpeg_params=["-movflags","+faststart"],
                    verbose=False,
                    logger=None
                )
            except Exception as e:
                st.error(f"MP4 파일 생성 실패: {e}")
                st.stop()

            # 결과 파일 다운로드
            try:
                with open(out_path, "rb") as f: 
                    data = f.read()
                st.success("완료! 아래 버튼으로 다운로드하세요.")
                st.download_button("📥 out.mp4 다운로드", data=data, file_name="out.mp4", mime="video/mp4")
            except Exception as e:
                st.error(f"파일 다운로드 준비 실패: {e}")
                st.stop()
            
            # 메모리 정리
            for clip in clips:
                clip.close()
            video.close()
            audio.close()
            gc.collect()
            
    except Exception as e:
        st.error(f"처리 중 오류가 발생했습니다: {e}")
        logger.error(f"전체 처리 오류: {e}", exc_info=True)
