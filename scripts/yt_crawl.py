#!/usr/bin/env python3
"""
yt_crawl.py - Flat metadata crawler for YouTube channels and playlists using yt-dlp.
Extracts video metadata (id, title, duration, view_count, url, upload_date) without downloading media.
"""

import sys
import json
import argparse
from pathlib import Path
import yt_dlp

# Ensure Windows stdout/stderr handles UTF-8 gracefully
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Extract flat video metadata from YouTube channels, playlists, or series using yt-dlp."
    )
    parser.add_argument("url", nargs="?", default=None, help="YouTube channel, handle, or playlist URL")
    parser.add_argument("output_dir", nargs="?", default=None, help="Output directory for channel_videos.json")
    parser.add_argument("--url", "-u", dest="flag_url", help="YouTube channel, handle, or playlist URL")
    parser.add_argument("--output-dir", "-o", dest="flag_output_dir", help="Output directory for channel_videos.json")
    parser.add_argument("--max-videos", "-m", type=int, default=None, help="Maximum number of videos to crawl")
    parser.add_argument("--include-shorts", action="store_true", default=False, help="Include YouTube Shorts (duration < 60s)")

    parsed_args = parser.parse_args(args)
    target_url = parsed_args.flag_url or parsed_args.url
    target_out_dir = parsed_args.flag_output_dir or parsed_args.output_dir

    if not target_url or not target_out_dir:
        parser.print_help()
        sys.exit(1)

    return target_url, target_out_dir, parsed_args.max_videos, parsed_args.include_shorts


def crawl_channel(url: str, out_dir: str, max_videos: int = None, include_shorts: bool = False):
    out_path = Path(out_dir) / "channel_videos.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android"]
            }
        }
    }

    print(f"[*] Crawling metadata from: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as err:
            print(f"[!] yt-dlp extraction error: {err}")
            info = None

        if not info:
            print("[!] No information returned by yt-dlp.")
            raw_entries = []
        elif info.get("entries") is not None:
            raw_entries = info["entries"]
        elif info.get("id"):
            raw_entries = [info]
        else:
            raw_entries = []

    videos = []
    skipped_private = 0
    skipped_shorts = 0

    for entry in raw_entries:
        if not entry or not isinstance(entry, dict):
            continue

        vid = entry.get("id")
        if not vid:
            continue

        title = (entry.get("title") or "").strip()
        # Filter private or deleted videos
        if not title or title in ["[Private video]", "[Deleted video]"] or "[Private video]" in title or "[Deleted video]" in title:
            skipped_private += 1
            continue

        # Duration handling (default: 600s if missing, null, or non-positive)
        raw_dur = entry.get("duration")
        if raw_dur is None:
            duration = 600
        else:
            try:
                val = int(round(float(raw_dur)))
                duration = val if val > 0 else 600
            except (ValueError, TypeError):
                duration = 600

        # Filter shorts if not requested
        if not include_shorts and duration < 60:
            skipped_shorts += 1
            continue

        view_count = entry.get("view_count")
        if view_count is not None:
            try:
                view_count = int(view_count)
            except (ValueError, TypeError):
                view_count = 0
        else:
            view_count = 0

        video_url = entry.get("url") or f"https://youtu.be/{vid}"
        if not str(video_url).startswith("http"):
            video_url = f"https://youtu.be/{vid}"

        video_record = {
            "id": vid,
            "title": title,
            "duration": duration,
            "view_count": view_count,
            "url": video_url,
        }
        if "upload_date" in entry and entry.get("upload_date"):
            video_record["upload_date"] = str(entry["upload_date"])

        videos.append(video_record)

        if max_videos and len(videos) >= max_videos:
            break

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    print(f"[*] Saved {len(videos)} videos to: {out_path}")
    if skipped_private > 0:
        print(f"[*] Filtered {skipped_private} private/deleted video(s)")
    if skipped_shorts > 0:
        print(f"[*] Filtered {skipped_shorts} short(s) (<60s)")

    return videos


def main():
    url, out_dir, max_videos, include_shorts = parse_args()
    crawl_channel(url, out_dir, max_videos, include_shorts)


if __name__ == "__main__":
    main()
