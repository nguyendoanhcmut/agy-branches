import sys
import json
import yt_dlp
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python yt_crawl.py <channel_url> <output_dir>")
    
    url, out_dir = sys.argv[1], sys.argv[2]
    out_path = Path(out_dir) / "channel_videos.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ydl_opts = {'extract_flat': True, 'quiet': True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        videos = [{k: e.get(k) for k in ('id', 'title', 'duration', 'view_count', 'url')} 
                  for e in info.get('entries', [])]

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2)

if __name__ == '__main__':
    main()
