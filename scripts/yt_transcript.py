import sys
import os
import json
import time
import argparse
import subprocess
from typing import List, Dict, Any, Union
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

DEFAULT_MAX_DURATION_SECONDS = 3600  # 60 minutes per batch
DEFAULT_VIDEO_DURATION_SECONDS = 600  # 10 minutes fallback if duration missing
API_BLOCKED = False


def bin_pack_videos(
    videos: List[Union[str, Dict[str, Any], tuple]],
    max_duration_seconds: int = DEFAULT_MAX_DURATION_SECONDS,
    default_duration: int = DEFAULT_VIDEO_DURATION_SECONDS,
    algorithm: str = "ffd"
) -> List[List[Dict[str, Any]]]:
    """
    Bin-packs YouTube videos into duration-constrained batches to maximize throughput
    while strictly avoiding rate limits (HTTP 429).
    
    Algorithms:
      - 'ffd' (First-Fit Decreasing): Sorts descending by duration, places into the first bin with room.
      - 'sequential': Preserves chronological/playlist order, filling bins greedily until capacity.
    """
    normalized = []
    for item in videos:
        if isinstance(item, str):
            normalized.append({"id": item, "duration": default_duration, "title": item})
        elif isinstance(item, dict):
            vid = item.get("id") or item.get("video_id")
            dur = item.get("duration")
            try:
                dur = float(dur) if dur is not None and float(dur) > 0 else default_duration
            except (ValueError, TypeError):
                dur = default_duration
            title = item.get("title", vid)
            normalized.append({"id": vid, "duration": dur, "title": title, **{k: v for k, v in item.items() if k not in ("id", "duration", "title")}})
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            vid = str(item[0])
            try:
                dur = float(item[1]) if item[1] is not None and float(item[1]) > 0 else default_duration
            except (ValueError, TypeError):
                dur = default_duration
            normalized.append({"id": vid, "duration": dur, "title": vid})

    if not normalized:
        return []

    if algorithm.lower() == "sequential":
        batches: List[List[Dict[str, Any]]] = []
        current_batch: List[Dict[str, Any]] = []
        current_dur = 0.0

        for v in normalized:
            vdur = v["duration"]
            if current_batch and (current_dur + vdur > max_duration_seconds):
                batches.append(current_batch)
                current_batch = [v]
                current_dur = vdur
            else:
                current_batch.append(v)
                current_dur += vdur
        if current_batch:
            batches.append(current_batch)
        return batches

    # Default: First-Fit Decreasing (FFD)
    sorted_videos = sorted(normalized, key=lambda x: x["duration"], reverse=True)
    bins: List[List[Dict[str, Any]]] = []
    bin_durations: List[float] = []

    for v in sorted_videos:
        vdur = v["duration"]
        placed = False
        for i in range(len(bins)):
            if bin_durations[i] + vdur <= max_duration_seconds:
                bins[i].append(v)
                bin_durations[i] += vdur
                placed = True
                break
        if not placed:
            bins.append([v])
            bin_durations.append(vdur)

    return bins


def get_transcript(vid: str, out_dir: str, pause_seconds: float = 0.5) -> Dict[str, Any]:
    """
    Downloads transcript for a single video.
    Tier 1: youtube_transcript_api (direct captions extraction)
    Tier 2: yt-dlp fallback (android client / auto-subs / description)
    """
    out_file = os.path.join(out_dir, f"{vid}.txt")
    if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
        return {"id": vid, "status": "cached", "path": out_file}

    global API_BLOCKED
    # Tier 1: YouTubeTranscriptApi
    if not API_BLOCKED:
        try:
            # Try Vietnamese, English, or any available transcript
            try:
                if hasattr(YouTubeTranscriptApi, 'get_transcript'):
                    try:
                        t = YouTubeTranscriptApi.get_transcript(vid, languages=['vi', 'en'])
                    except Exception:
                        t = YouTubeTranscriptApi.get_transcript(vid)
                    text = TextFormatter().format_transcript(t)
                else:
                    api = YouTubeTranscriptApi()
                    try:
                        t = api.fetch(vid, languages=['vi', 'en'])
                    except Exception:
                        t = api.fetch(vid)
                    text = "\n".join([f"[{getattr(s, 'start', 0.0):.1f}s] {getattr(s, 'text', '')}" for s in t.snippets])
            except Exception:
                raise

            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(text)
            time.sleep(pause_seconds)
            return {"id": vid, "status": "success", "method": "api", "path": out_file, "word_count": len(text.split())}
        except Exception as e:
            if "blocked" in str(e).lower() or "ipblocked" in str(e).lower() or "requestblocked" in str(e).lower():
                API_BLOCKED = True
                print(f"[yt_transcript] API blocked detected, switching to yt-dlp fallback for all videos.")
            else:
                print(f"[{vid}] API failed, falling back to yt-dlp...")

    # Tier 2: yt-dlp fallback
    try:
        subprocess.run([
            'yt-dlp',
            '--extractor-args', 'youtube:player_client=android',
            '--write-auto-sub', '--write-sub', '--write-description',
            '--skip-download', '-o', f'{out_dir}/%(id)s.%(ext)s',
            f'https://youtu.be/{vid}'
        ], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Check if text or sub files exist and normalize to {vid}.txt
        import glob
        vtt_matches = glob.glob(os.path.join(out_dir, f"{vid}*.vtt"))
        sub_candidate = None
        if vtt_matches:
            sub_candidate = vtt_matches[0]
        elif os.path.exists(os.path.join(out_dir, f"{vid}.description")):
            sub_candidate = os.path.join(out_dir, f"{vid}.description")

        if sub_candidate:
            with open(sub_candidate, 'r', encoding='utf-8', errors='ignore') as sf:
                sub_content = sf.read()
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(sub_content)
            time.sleep(pause_seconds)
            return {"id": vid, "status": "success", "method": "yt-dlp", "path": out_file, "word_count": len(sub_content.split())}
        else:
            return {"id": vid, "status": "failed", "error": "No subtitles or description retrieved via yt-dlp"}
    except Exception as e_dlp:
        return {"id": vid, "status": "failed", "error": str(e_dlp)}


def fetch_transcripts_packed(
    videos: List[Union[str, Dict[str, Any]]],
    out_dir: str,
    max_duration_seconds: int = DEFAULT_MAX_DURATION_SECONDS,
    pause_between_batches: float = 2.0,
    algorithm: str = "ffd"
) -> Dict[str, Any]:
    """
    Executes batched fetching with duration bin-packing.
    """
    os.makedirs(out_dir, exist_ok=True)
    batches = bin_pack_videos(videos, max_duration_seconds=max_duration_seconds, algorithm=algorithm)
    
    print(f"[yt_transcript] Bin-packed {len(videos)} videos into {len(batches)} batches (max {max_duration_seconds // 60} min/batch)")
    
    results = []
    for b_idx, batch in enumerate(batches, start=1):
        batch_dur_min = sum(v["duration"] for v in batch) / 60.0
        print(f" -> Processing Batch {b_idx}/{len(batches)}: {len(batch)} videos ({batch_dur_min:.1f} total mins)")
        for v in batch:
            res = get_transcript(v["id"], out_dir)
            v_res = {**v, **res}
            results.append(v_res)
            print(f"    * [{res['status'].upper()}] {v['id']} - {v.get('title', '')[:50]}")
        
        if b_idx < len(batches):
            print(f"    [Pacing] Sleeping {pause_between_batches}s to prevent rate limits...")
            time.sleep(pause_between_batches)

    manifest_path = os.path.join(out_dir, "transcript_manifest.json")
    summary = {
        "total_videos": len(videos),
        "total_batches": len(batches),
        "succeeded": sum(1 for r in results if r.get("status") in ("success", "cached")),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
        "batch_duration_cap_minutes": max_duration_seconds // 60,
        "results": results
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"[yt_transcript] Finished: {summary['succeeded']}/{summary['total_videos']} transcripts ready. Manifest: {manifest_path}")
    return summary


def main():
    # Backward compatibility check: "python yt_transcript.py <out_dir> <vid1> [vid2...]"
    if len(sys.argv) >= 3 and not sys.argv[1].startswith("--"):
        out_dir = sys.argv[1]
        vids = sys.argv[2:]
        fetch_transcripts_packed(vids, out_dir)
        return

    parser = argparse.ArgumentParser(description="YouTube Transcript Fetcher with Adaptive Duration Bin-Packing")
    parser.add_argument("--out", "-o", help="Output directory for transcripts", default="transcripts")
    parser.add_argument("--vids", nargs="*", help="List of video IDs")
    parser.add_argument("--videos", help="Path to channel_videos.json")
    parser.add_argument("--catalog", help="Path to topic_catalog.json")
    parser.add_argument("--topic", help="Topic ID or name to filter from catalog")
    parser.add_argument("--max-duration", type=int, default=DEFAULT_MAX_DURATION_SECONDS, help="Max duration per batch in seconds (default 3600)")
    parser.add_argument("--algorithm", choices=["ffd", "sequential"], default="ffd", help="Bin-packing algorithm (ffd or sequential)")
    parser.add_argument("--plan-only", action="store_true", help="Print bin-packing plan without downloading")

    args = parser.parse_args()

    video_items = []
    if args.vids:
        video_items.extend(args.vids)
    elif args.catalog and os.path.exists(args.catalog):
        with open(args.catalog, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        topics = catalog.get("topics", [])
        selected_topics = topics
        if args.topic:
            selected_topics = [
                t for t in topics
                if str(t.get("id")) == str(args.topic) or args.topic.lower() in t.get("name", "").lower()
            ]
        for t in selected_topics:
            video_items.extend(t.get("videos", []))
    elif args.videos and os.path.exists(args.videos):
        with open(args.videos, "r", encoding="utf-8") as f:
            video_items = json.load(f)

    if not video_items:
        print("Usage: python yt_transcript.py <out_dir> <vid1> [vid2...]")
        print("   OR: python yt_transcript.py --out <dir> [--videos <file> | --catalog <file> [--topic <id>]]")
        sys.exit(1)

    if args.plan_only:
        batches = bin_pack_videos(video_items, max_duration_seconds=args.max_duration, algorithm=args.algorithm)
        plan = {
            "total_videos": len(video_items),
            "batch_count": len(batches),
            "batches": [
                {
                    "batch_index": i + 1,
                    "video_count": len(b),
                    "total_duration_minutes": round(sum(v["duration"] for v in b) / 60, 2),
                    "video_ids": [v["id"] for v in b]
                }
                for i, b in enumerate(batches)
            ]
        }
        print(json.dumps(plan, indent=2))
        return

    fetch_transcripts_packed(
        video_items,
        out_dir=args.out,
        max_duration_seconds=args.max_duration,
        algorithm=args.algorithm
    )


if __name__ == "__main__":
    main()

