import sys
import os
import subprocess
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

def get_transcript(vid, out_dir):
    out_file = os.path.join(out_dir, f"{vid}.txt")
    if os.path.exists(out_file): return
    try:
        t = YouTubeTranscriptApi.get_transcript(vid)
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(TextFormatter().format_transcript(t))
    except Exception as e:
        print(f"{vid} failed ({e}), falling back to yt-dlp...")
        subprocess.run([
            'yt-dlp', 
            '--extractor-args', 'youtube:player_client=android',
            '--write-auto-sub', '--write-sub', '--write-description', 
            '--skip-download', '-o', f'{out_dir}/%(id)s.%(ext)s',
            f'https://youtu.be/{vid}'
        ], check=False)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python yt_transcript.py <out_dir> <vid1> [vid2...]")
        sys.exit(1)
    os.makedirs(sys.argv[1], exist_ok=True)
    for vid in sys.argv[2:]:
        get_transcript(vid, sys.argv[1])
