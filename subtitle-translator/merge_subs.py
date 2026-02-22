import sys
import argparse
from pathlib import Path
import pysrt

def merge_srt(original_path, translated_path, output_path):
    orig_subs = pysrt.open(str(original_path))
    trans_subs = pysrt.open(str(translated_path))
    
    # Ensure lengths match or handle mismatch
    limit = min(len(orig_subs), len(trans_subs))
    if len(orig_subs) != len(trans_subs):
        print(
            f"Warning: subtitle length mismatch (original={len(orig_subs)}, translated={len(trans_subs)}). "
            f"Only first {limit} entries will be merged."
        )
    
    for i in range(limit):
        orig_text = orig_subs[i].text.strip()
        trans_text = trans_subs[i].text.strip()
        
        # Combined format: Translated \n Original
        # If translation is empty, just use original
        if trans_text:
            combined = f"{trans_text}\n{orig_text}"
        else:
            combined = orig_text
            
        orig_subs[i].text = combined
        
    orig_subs.save(str(output_path), encoding='utf-8')
    print(f"Saved bilingual subtitles to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python merge_subs.py <original_srt> <translated_srt> [output_srt]")
        sys.exit(1)
        
    orig = Path(sys.argv[1])
    trans = Path(sys.argv[2])
    
    if len(sys.argv) >= 4:
        out = Path(sys.argv[3])
    else:
        out = orig.parent / f"{orig.stem}.bilingual.srt"
        
    merge_srt(orig, trans, out)
