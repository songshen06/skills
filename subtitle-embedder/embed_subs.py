import argparse
import json
import subprocess
import sys
import shutil
from pathlib import Path

try:
    import pysrt
except ImportError:
    pysrt = None

def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg is not installed or not in PATH.")
        print("Please install ffmpeg using: brew install ffmpeg")
        sys.exit(1)


def _time_to_ms(ts):
    return (
        ((int(ts.hours) * 60 + int(ts.minutes)) * 60 + int(ts.seconds)) * 1000
        + int(ts.milliseconds)
    )


def _match_subtitle_text(primary_item, secondary_subs, idx_hint):
    """Find best subtitle text by nearest start time around index hint."""
    if not secondary_subs:
        return ""
    candidates = []
    for idx in (idx_hint - 1, idx_hint, idx_hint + 1):
        if 0 <= idx < len(secondary_subs):
            candidates.append((idx, secondary_subs[idx]))
    if not candidates:
        return ""

    p_start = _time_to_ms(primary_item.start)
    best_idx = candidates[0][0]
    best_dist = abs(_time_to_ms(candidates[0][1].start) - p_start)
    for idx, item in candidates[1:]:
        dist = abs(_time_to_ms(item.start) - p_start)
        if dist < best_dist:
            best_idx = idx
            best_dist = dist

    # If time gap is too large, skip pairing to avoid wrong bilingual lines.
    if best_dist > 1500:
        return ""
    return secondary_subs[best_idx].text


def _escape_subtitles_filter_path(path):
    value = str(Path(path).resolve())
    value = value.replace("\\", "\\\\")
    value = value.replace(":", "\\:")
    value = value.replace("'", "\\'")
    return value


def merge_subtitles(sub1_path, sub2_path, output_path):
    """Merge two SRT files into one bilingual SRT."""
    if not pysrt:
        print("Error: pysrt is required for merging subtitles.")
        print("Please install it: pip install pysrt")
        sys.exit(1)
        
    subs1 = pysrt.open(str(sub1_path))
    subs2 = pysrt.open(str(sub2_path))
    
    # Simple merge strategy: Iterate through subs1, find matching time in subs2
    # Or just index matching if they are from the same source (Whisper + Translation)
    # Assuming line-by-line correspondence for translated subs
    
    # Create new subtitle object
    merged_subs = pysrt.SubRipFile()
    
    limit = len(subs1)
    for i in range(limit):
        item1 = subs1[i]
        text2 = _match_subtitle_text(item1, subs2, i)
        
        new_item = pysrt.SubRipItem(
            index=i + 1,
            start=item1.start,
            end=item1.end,
            text=f"{text2}\n{item1.text}" if text2 else item1.text,
        )
        merged_subs.append(new_item)
        
    merged_subs.save(str(output_path), encoding='utf-8')
    return output_path

def embed_subtitle(video_path, subtitle_path, output_path=None, soft_subs=True, lang="chi", secondary_subtitle=None, secondary_lang="eng"):
    video_path = Path(video_path)
    subtitle_path = Path(subtitle_path)
    
    if not video_path.exists():
        return {"status": "failed", "error": f"Video file not found: {video_path}"}
        
    if not subtitle_path.exists():
        return {"status": "failed", "error": f"Subtitle file not found: {subtitle_path}"}

    if secondary_subtitle:
        secondary_subtitle = Path(secondary_subtitle)
        if not secondary_subtitle.exists():
             return {"status": "failed", "error": f"Secondary subtitle file not found: {secondary_subtitle}"}

    if output_path is None:
        # Default output name: video_name.embedded.mp4
        output_path = video_path.parent / f"{video_path.stem}.embedded{video_path.suffix}"
    else:
        output_path = Path(output_path)

    print(f"Processing:\n Video: {video_path}\n Subtitle: {subtitle_path}")
    if secondary_subtitle:
        print(f" Secondary Subtitle: {secondary_subtitle}")
    print(f" Output: {output_path}")

    # Handle Bilingual Logic
    final_sub_path = subtitle_path
    temp_merged_sub = None
    
    # If Hard Subs and Secondary provided -> Force Merge
    if not soft_subs and secondary_subtitle:
        print("Merging subtitles for hard burn-in...")
        temp_merged_sub = video_path.parent / "temp_merged_bilingual.srt"
        # Merge: subtitle_path (Primary/Bottom), secondary_subtitle (Secondary/Top)
        # Assuming user passes: Primary (CN), Secondary (EN)
        # We want:
        # EN
        # CN
        # So in merge function: text = secondary + \n + primary
        merge_subtitles(subtitle_path, secondary_subtitle, temp_merged_sub)
        final_sub_path = temp_merged_sub

    cmd = ["ffmpeg", "-y", "-i", str(video_path)]

    if soft_subs:
        print("Mode: Soft Subtitles (Muxing)")
        
        cmd.extend(["-i", str(subtitle_path)])
        stream_map = ["-map", "0", "-map", "1"]
        
        metadata = [f"-metadata:s:s:0", f"language={lang}"]
        
        if secondary_subtitle:
            print("Adding secondary subtitle stream...")
            cmd.extend(["-i", str(secondary_subtitle)])
            stream_map.extend(["-map", "2"])
            metadata.extend([f"-metadata:s:s:1", f"language={secondary_lang}"])
            
        cmd.extend(stream_map)
        cmd.extend(["-c:v", "copy", "-c:a", "copy"])
        
        if output_path.suffix.lower() == ".mp4":
            cmd.extend(["-c:s", "mov_text"])
        elif output_path.suffix.lower() == ".mkv":
             cmd.extend(["-c:s", "srt"])
        else:
             pass
             
        cmd.extend(metadata)

    else:
        print("Mode: Hard Subtitles (Burning)")
        
        # Use final_sub_path (which might be the merged one)
        # Using libx264 for compatibility
        # Windows path escaping issues might occur, but assuming macOS/Linux here
        # style: Force alignment 2 (Bottom Center) and maybe some font size if needed, but default is usually ok
        sub_filter_path = _escape_subtitles_filter_path(final_sub_path)
        cmd.extend(["-vf", f"subtitles='{sub_filter_path}':force_style='Alignment=2'"])
        cmd.extend(["-c:a", "copy"]) 
        # Re-encode video
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])

    cmd.append(str(output_path))

    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("\nSuccess! Output saved to:", output_path)
        result = {
            "status": "success",
            "mode": "soft" if soft_subs else "hard",
            "video": str(video_path),
            "subtitle": str(subtitle_path),
            "secondary_subtitle": str(secondary_subtitle) if secondary_subtitle else None,
            "output": str(output_path),
        }
    except subprocess.CalledProcessError as e:
        print("\nError running ffmpeg:", e)
        # Clean up temp file
        if temp_merged_sub and temp_merged_sub.exists():
            temp_merged_sub.unlink()
        return {
            "status": "failed",
            "error": str(e),
            "mode": "soft" if soft_subs else "hard",
            "video": str(video_path),
            "output": str(output_path),
        }
        
    # Clean up temp file
    if temp_merged_sub and temp_merged_sub.exists():
        temp_merged_sub.unlink()
    return result

def main():
    parser = argparse.ArgumentParser(description="Embed subtitles into video using ffmpeg.")
    parser.add_argument("video", help="Path to input video file")
    parser.add_argument("subtitle", help="Path to input subtitle file (Primary)")
    parser.add_argument("secondary_subtitle", nargs="?", help="Path to secondary subtitle file (Optional, for bilingual)")
    parser.add_argument("-o", "--output", help="Path to output video file")
    parser.add_argument("--hard", action="store_true", help="Burn subtitles into video (Hard Subs). Default is Soft Subs (Mux).")
    parser.add_argument("--lang", default="chi", help="Language code for primary soft subs (e.g., chi). Default: chi")
    parser.add_argument("--lang2", default="eng", help="Language code for secondary soft subs (e.g., eng). Default: eng")

    args = parser.parse_args()
    
    check_ffmpeg()
    result = embed_subtitle(
        args.video, 
        args.subtitle, 
        args.output, 
        not args.hard, 
        args.lang,
        args.secondary_subtitle,
        args.lang2
    )
    print(json.dumps(result, ensure_ascii=False))
    if result.get("status") != "success":
        sys.exit(1)

if __name__ == "__main__":
    main()
