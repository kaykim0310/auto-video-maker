# CLI: sync_slides_to_audio.py

CSV(`filename,start_time`)와 오디오, 이미지 폴더를 받아 **MP4**를 생성합니다.

## 사용 예
```bash
python cli/sync_slides_to_audio.py   --audio narration.wav   --csv slides_timing_sample.csv   --images_dir ./sample/slides   --out out.mp4   --size 1920x1080   --fps 30
```
