#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cli/sync_slides_to_audio.py
이미지(슬라이드)와 오디오를 지정된 시작시각표에 맞춰 합쳐서 동영상을 만드는 스크립트.
- 입력: CSV (columns: filename,start_time), 오디오 파일(mp3/wav 등)
- 출력: MP4(H.264 + AAC)
- 의존성: moviepy, pandas
"""
import argparse, os, re
from typing import Tuple, List
import pandas as pd
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

def parse_size(size_str: str) -> Tuple[int,int]:
    m = re.match(r'^(\d+)x(\d+)$', size_str.strip())
    if not m:
        raise ValueError("--size 형식이 잘못되었습니다: %s (예: 1920x1080)" % size_str)
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

def load_timing(csv_path: str, images_dir: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if 'filename' not in df.columns or 'start_time' not in df.columns:
        raise ValueError("CSV에는 'filename','start_time' 두 컬럼이 반드시 있어야 합니다.")
    df['filepath'] = df['filename'].apply(lambda f: os.path.join(images_dir, str(f)))
    for p in df['filepath']:
        if not os.path.isfile(p):
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {p}")
    df['start_sec'] = df['start_time'].apply(parse_time_to_seconds)
    df = df.sort_values('start_sec', ascending=True).reset_index(drop=True)
    if not df['start_sec'].is_monotonic_increasing:
        raise ValueError("start_time(초)이 오름차순이 아닙니다. 동일 시간은 허용되지만 감소는 허용되지 않습니다.")
    return df

def fit_image_clip(path: str, duration: float, target_w: int, target_h: int) -> ImageClip:
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

def build_video(audio_path: str, df: pd.DataFrame, out_path: str,
                size: str = "1920x1080", fps: int = 30, end_padding: float = 0.0):
    target_w, target_h = parse_size(size)
    audio = AudioFileClip(audio_path)
    audio_duration = float(audio.duration)
    starts = df['start_sec'].tolist()
    durations = []
    for i, s in enumerate(starts):
        if i < len(starts) - 1:
            d = max(0.01, starts[i+1] - s)
        else:
            d = max(0.01, audio_duration - s + end_padding)
        durations.append(d)
    clips: List[ImageClip] = []
    for img_path, dur in zip(df['filepath'], durations):
        clip = fit_image_clip(img_path, dur, target_w, target_h)
        clips.append(clip)
    video = concatenate_videoclips(clips, method="compose")
    final_duration = max(video.duration, audio_duration + end_padding)
    video = video.set_duration(final_duration).set_audio(audio.set_duration(final_duration))
    video.write_videofile(
        out_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        ffmpeg_params=["-movflags","+faststart"]
    )

def main():
    ap = argparse.ArgumentParser(description="오디오 타이밍에 맞춰 슬라이드 이미지 붙여서 MP4 만들기")
    ap.add_argument("--audio", required=True, help="오디오 파일 경로 (mp3, wav 등)")
    ap.add_argument("--csv", required=True, help="슬라이드 타이밍 CSV 경로 (filename,start_time)")
    ap.add_argument("--images_dir", required=True, help="이미지(슬라이드) 폴더 경로")
    ap.add_argument("--out", default="out.mp4", help="출력 MP4 경로 (기본: out.mp4)")
    ap.add_argument("--size", default="1920x1080", help="출력 해상도 WxH (기본: 1920x1080)")
    ap.add_argument("--fps", type=int, default=30, help="프레임레이트 (기본: 30)")
    ap.add_argument("--end_padding", type=float, default=0.0, help="오디오 끝 이후 여유 구간(초)")
    args = ap.parse_args()
    df = load_timing(args.csv, args.images_dir)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    build_video(args.audio, df, args.out, size=args.size, fps=args.fps, end_padding=args.end_padding)
    print(f"[완료] 생성된 영상: {args.out}")

if __name__ == "__main__":
    main()
