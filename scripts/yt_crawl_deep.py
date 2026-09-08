#!/usr/bin/env python3
"""
yt_crawl_deep.py - Deep metadata crawler for YouTube channels using yt-dlp.

Enriches flat video listings (id, title, duration, view_count, url) with:
  - description
  - chapters (parsed titles and timestamps)
  - tags
  - categories

Optimized for high-throughput, lightweight metadata acquisition without downloading
video formats, manifests (HLS/DASH), or executing JS engines.
"""

import os
import sys
import json
import time
import argparse
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import yt_dlp

# Ensure Windows stdout/stderr handles UTF-8 gracefully
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_thread_local = threading.local()


def get_thread_ydl() -> yt_dlp.YoutubeDL:
    """Returns a thread-local YoutubeDL instance configured for fast metadata-only extraction."""
    if not hasattr(_thread_local, "ydl"):
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "simulate": True,
            "extract_flat": False,
            "extractor_args": {
                "youtube": {
                    "skip": ["hls", "dash", "translated_subs"],
                    "player_skip": ["js", "configs"],
                }
            },
        }
        _thread_local.ydl = yt_dlp.YoutubeDL(ydl_opts)
    return _thread_local.ydl


def extract_video_metadata(video: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts deep metadata (description, chapters, tags, categories) for a single video.
    """
    vid = video.get("id")
    url = video.get("url") or f"https://www.youtube.com/watch?v={vid}"
    title = video.get("title", vid)

    enriched = dict(video)
    t0 = time.time()

    try:
        ydl = get_thread_ydl()
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("No info returned by yt-dlp")

        # Clean chapters
        raw_chapters = info.get("chapters") or []
        chapters = []
        for ch in raw_chapters:
            chapters.append({
                "title": ch.get("title", ""),
                "start_time": ch.get("start_time", 0),
                "end_time": ch.get("end_time", 0)
            })

        enriched["description"] = info.get("description") or ""
        enriched["tags"] = info.get("tags") or []
        enriched["categories"] = info.get("categories") or []
        enriched["chapters"] = chapters
        if "upload_date" in info:
            enriched["upload_date"] = info.get("upload_date")
        enriched["status"] = "success"

    except Exception as e:
        # Graceful fallback: retain video item with empty metadata
        enriched["description"] = ""
        enriched["tags"] = []
        enriched["categories"] = []
        enriched["chapters"] = []
        enriched["status"] = f"failed: {e}"

    elapsed = time.time() - t0
    enriched["_crawl_time"] = round(elapsed, 2)
    return enriched


def sample_videos(videos: List[Dict[str, Any]], sample_size: int, mode: str = "systematic") -> List[Dict[str, Any]]:
    """
    Selects a representative sample of videos from the full list.

    Modes:
      - 'systematic': Evenly spaced across the chronological list to capture all channel eras.
      - 'top-views': Highest view count videos.
      - 'recent': Most recent videos (beginning of list).
      - 'all': All videos.
    """
    total = len(videos)
    if sample_size <= 0 or sample_size >= total or mode == "all":
        return videos

    if mode == "recent":
        return videos[:sample_size]

    if mode == "top-views":
        return sorted(videos, key=lambda v: v.get("view_count") or 0, reverse=True)[:sample_size]

    # Default: 'systematic'
    step = total / sample_size
    sampled = []
    seen_ids = set()
    for i in range(sample_size):
        idx = min(int(i * step), total - 1)
        v = videos[idx]
        if v.get("id") not in seen_ids:
            sampled.append(v)
            seen_ids.add(v.get("id"))

    # If minor rounding reduced count, fill in sequentially
    if len(sampled) < sample_size:
        for v in videos:
            if v.get("id") not in seen_ids:
                sampled.append(v)
                seen_ids.add(v.get("id"))
                if len(sampled) == sample_size:
                    break

    return sampled


def crawl_deep_metadata(
    input_path: str,
    output_path: str,
    sample_size: int = 150,
    sample_mode: str = "systematic",
    workers: int = 6,
    checkpoint_interval: int = 10
) -> List[Dict[str, Any]]:
    """
    Crawls deep metadata for the specified sample of videos in parallel.
    Supports incremental checkpoints and resuming from existing output files.
    """
    in_file = Path(input_path)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if not in_file.exists():
        raise FileNotFoundError(f"Input file not found: {in_file}")

    with open(in_file, "r", encoding="utf-8") as f:
        all_videos = json.load(f)

    print(f"[*] Loaded {len(all_videos)} total videos from: {in_file}")

    target_videos = sample_videos(all_videos, sample_size, mode=sample_mode)
    print(f"[*] Selected {len(target_videos)} videos using '{sample_mode}' sampling (target: {sample_size})")

    # Check for existing enriched items to resume/skip
    cached_map: Dict[str, Dict[str, Any]] = {}
    if out_file.exists() and out_file.stat().st_size > 0:
        try:
            with open(out_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    for item in existing_data:
                        vid = item.get("id")
                        # Valid cache if it has description or tags or categories or chapters
                        if vid and ("description" in item or "tags" in item):
                            cached_map[vid] = item
            print(f"[*] Found {len(cached_map)} existing enriched videos in output file. Reusing cache.")
        except Exception as e:
            print(f"[!] Warning reading existing output file: {e}")

    results_by_id: Dict[str, Dict[str, Any]] = {}
    to_fetch: List[Dict[str, Any]] = []

    for v in target_videos:
        vid = v.get("id")
        if vid in cached_map:
            results_by_id[vid] = cached_map[vid]
        else:
            to_fetch.append(v)

    print(f"[*] Already cached: {len(results_by_id)} | Remaining to fetch: {len(to_fetch)}")

    save_lock = threading.Lock()

    def save_current_results():
        with save_lock:
            # Preserve target sample ordering
            ordered = [results_by_id[v["id"]] for v in target_videos if v["id"] in results_by_id]
            temp_file = out_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as tf:
                json.dump(ordered, tf, indent=2, ensure_ascii=False)
            temp_file.replace(out_file)

    if not to_fetch:
        print("[*] All target videos are already enriched. Saving final output.")
        save_current_results()
        return [results_by_id[v["id"]] for v in target_videos if v["id"] in results_by_id]

    print(f"[*] Starting parallel extraction with {workers} worker threads...")
    start_time = time.time()
    completed_count = len(results_by_id)
    total_target = len(target_videos)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(extract_video_metadata, v): v for v in to_fetch}

        for future in as_completed(futures):
            v_orig = futures[future]
            try:
                enriched = future.result()
            except Exception as e:
                enriched = dict(v_orig)
                enriched["status"] = f"error: {e}"
                enriched["description"] = ""
                enriched["tags"] = []
                enriched["categories"] = []
                enriched["chapters"] = []

            vid = enriched.get("id")
            results_by_id[vid] = enriched
            completed_count += 1

            # Progress log
            status_tag = enriched.get("status", "ok")
            n_ch = len(enriched.get("chapters") or [])
            n_tags = len(enriched.get("tags") or [])
            elapsed_sec = enriched.get("_crawl_time", 0.0)
            title_trunc = enriched.get("title", vid)[:45]
            pct = (completed_count / total_target) * 100

            print(f"[{completed_count:3d}/{total_target:3d}] ({pct:5.1f}%) [{status_tag:7s}] "
                  f"{vid}: {title_trunc:<45} | ch:{n_ch:2d} tags:{n_tags:2d} ({elapsed_sec:.1f}s)")

            if completed_count % checkpoint_interval == 0:
                save_current_results()

    # Final save
    save_current_results()
    total_time = time.time() - start_time
    avg_per_video = total_time / len(to_fetch) if to_fetch else 0.0

    ordered_results = [results_by_id[v["id"]] for v in target_videos if v["id"] in results_by_id]
    has_chapters = sum(1 for v in ordered_results if v.get("chapters"))
    has_tags = sum(1 for v in ordered_results if v.get("tags"))
    has_desc = sum(1 for v in ordered_results if v.get("description"))

    print("\n" + "=" * 70)
    print(f"[OK] Completed Deep Metadata Crawl!")
    print(f"    - Output: {out_file} ({out_file.stat().st_size:,} bytes)")
    print(f"    - Total target videos: {len(ordered_results)}")
    print(f"    - Freshly crawled: {len(to_fetch)} in {total_time:.2f}s ({avg_per_video:.2f}s/video)")
    print(f"    - Videos with chapters: {has_chapters}/{len(ordered_results)} ({has_chapters / len(ordered_results) * 100:.1f}%)")
    print(f"    - Videos with tags:     {has_tags}/{len(ordered_results)} ({has_tags / len(ordered_results) * 100:.1f}%)")
    print(f"    - Videos with desc:     {has_desc}/{len(ordered_results)} ({has_desc / len(ordered_results) * 100:.1f}%)")
    print("=" * 70)

    return ordered_results


def main():
    parser = argparse.ArgumentParser(
        description="Deep Metadata Crawler: Enriches YouTube channel videos with descriptions, chapters, tags, and categories."
    )
    parser.add_argument(
        "--input", "-i",
        help="Path to input channel_videos.json",
        default="channel_videos.json"
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to output channel_videos_enriched.json",
        default="channel_videos_enriched.json"
    )
    parser.add_argument(
        "--sample-size", "-n",
        type=int,
        default=150,
        help="Number of videos to sample (default: 150). Set to 0 to crawl all."
    )
    parser.add_argument(
        "--sample-mode",
        choices=["systematic", "recent", "top-views", "all"],
        default="systematic",
        help="Sampling strategy (default: systematic - evenly spaced across timeline)"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=6,
        help="Number of parallel worker threads (default: 6)"
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=10,
        help="Save checkpoint every N videos (default: 10)"
    )

    args = parser.parse_args()

    crawl_deep_metadata(
        input_path=args.input,
        output_path=args.output,
        sample_size=args.sample_size,
        sample_mode=args.sample_mode,
        workers=args.workers,
        checkpoint_interval=args.checkpoint_interval
    )


if __name__ == "__main__":
    main()
