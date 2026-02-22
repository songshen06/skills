import os
import sys
import argparse
import json
from pathlib import Path
import re
from typing import List, Tuple
import asyncio
import random

# Third-party libraries
try:
    from openai import AsyncOpenAI, RateLimitError, APIStatusError, APITimeoutError
    import pysrt
    import webvtt
    from dotenv import load_dotenv
    from tqdm.asyncio import tqdm
    from deep_translator import GoogleTranslator
except ImportError as e:
    print(f"Error: Missing dependency {e.name}. Please install required packages:")
    print("pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables
# 1. Try loading from the current directory
load_dotenv()
# 2. Try loading from the project root (assuming script is deep in .trae/skills/...)
project_root = Path(__file__).resolve().parents[3]
load_dotenv(project_root / ".env")

# Configuration
DEFAULT_API_BASE = "https://inference-api.nvidia.com/v1"
DEFAULT_LLM_MODEL = "nvidia/qwen/qwen3-next-80b-a3b-instruct"
DEFAULT_OLLAMA_MODEL = "translategemma:4b"


def sanitize_target_lang(name: str) -> str:
    """Make target language safe for filenames."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "").strip())
    safe = safe.strip("._-")
    return safe or "translated"

def get_client(api_key=None, base_url=None):
    """Initialize OpenAI client."""
    # 1. args (passed as api_key/base_url params)
    # 2. env vars
    # 3. defaults
    
    # Resolve Base URL
    base_url = base_url or os.getenv("API_BASE_URL") or DEFAULT_API_BASE
    
    # Resolve API Key
    # If using local LLM (localhost/127.0.0.1), default key to "lm-studio" if not provided
    is_local = "localhost" in base_url or "127.0.0.1" in base_url
    default_key = "lm-studio" if is_local else None
    
    api_key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY") or default_key
    
    if not api_key:
        print("Error: API Key not found. Please set NVIDIA_API_KEY or OPENAI_API_KEY in .env file or environment.")
        print("For local LLMs (LM Studio/Ollama), ensure --api-base is set to localhost.")
        sys.exit(1)
    
    return AsyncOpenAI(base_url=base_url, api_key=api_key)

def parse_args():
    parser = argparse.ArgumentParser(description="Translate subtitle files (SRT, VTT, TXT) using AI.")
    parser.add_argument("input_path", help="Path to input file or directory")
    parser.add_argument("--target-lang", "-t", required=True, help="Target language (e.g., 'Chinese', 'Spanish')")
    parser.add_argument("--model", "-m", help="AI Model to use")
    parser.add_argument("--output-dir", "-o", help="Directory to save translated files (default: same as input)")
    parser.add_argument("--batch-size", "-b", type=int, default=10, help="Number of lines/blocks to translate at once")
    parser.add_argument("--concurrency", "-c", type=int, default=5, help="Number of concurrent API calls")
    parser.add_argument("--service", "-s", choices=["llm", "google", "ollama"], default="llm", help="Translation service to use (llm, google, or ollama)")
    parser.add_argument("--api-base", help="API Base URL (e.g. http://localhost:1234/v1 for LM Studio)")
    parser.add_argument("--api-key", help="API Key (optional for local LLMs)")
    parser.add_argument("--bilingual", action="store_true", help="Output bilingual subtitles (Target Language \\n Original Language)")
    return parser.parse_args()

# Simple language mapping for Google Translate
# Google Translate requires ISO codes (e.g. zh-CN, en, ja)
LANG_MAP = {
    "chinese": "zh-CN",
    "zh": "zh-CN",
    "mandarin": "zh-CN",
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "japanese": "ja",
    "korean": "ko",
    "russian": "ru",
    "italian": "it",
    "portuguese": "pt",
}

def get_google_lang_code(lang_name):
    """Convert natural language name to Google Translate code."""
    lang_lower = lang_name.lower()
    if lang_lower in LANG_MAP:
        return LANG_MAP[lang_lower]
    # Return as is if not found (user might have provided a code)
    return lang_name

def read_srt(file_path):
    """Read SRT file and return list of (start, end, text) tuples."""
    subs = pysrt.open(str(file_path))
    return [(sub.start, sub.end, sub.text) for sub in subs], subs

def read_vtt(file_path):
    """Read VTT file and return list of (start, end, text) tuples."""
    subs = webvtt.read(str(file_path))
    return [(sub.start, sub.end, sub.text) for sub in subs], subs

def read_txt(file_path):
    """Read TXT file and return list of (None, None, text) tuples."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    return [(None, None, line) for line in lines], lines

async def call_with_retry(func, *args, **kwargs):
    """Execute an async function with exponential backoff and jitter."""
    max_retries = 8
    base_delay = 2.0
    factor = 2.0
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                print(f"\nMax retries hit for RateLimit: {e}")
                raise e
            # Exponential backoff + Jitter
            delay = (base_delay * (factor ** attempt)) + random.uniform(0, 1)
            print(f"\nRate limit hit (429). Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)
        except APITimeoutError as e:
             if attempt == max_retries - 1:
                print(f"\nMax retries hit for Timeout: {e}")
                raise e
             print(f"\nTimeout. Retrying...")
             await asyncio.sleep(2)
        except APIStatusError as e:
            if e.status_code >= 500:
                if attempt == max_retries - 1:
                    print(f"\nMax retries hit for Server Error: {e}")
                    raise e
                delay = (base_delay * (factor ** attempt)) + random.uniform(0, 1)
                print(f"\nServer error {e.status_code}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
            else:
                raise e
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            raise e

async def translate_batch(client, texts: List[str], target_lang: str, model: str, index: int) -> Tuple[int, List[str], dict]:
    """Translate a batch of texts using the AI model."""
    if not texts:
        return index, [], {"batch_error": False, "line_fallback_failures": 0}

    # Construct prompt
    prompt = f"Translate the following subtitles to {target_lang}. Maintain the tone and context. Return ONLY the translated lines, one per line, corresponding exactly to the input lines. Do not include numbering or any other text.\n\nInput:\n"
    for i, text in enumerate(texts):
        # Remove newlines within a subtitle block to avoid confusion, or handle them carefully
        clean_text = text.replace('\n', ' ') 
        prompt += f"{clean_text}\n"

    async def _api_call():
        return await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional subtitle translator. You translate text accurately while preserving the original meaning and nuance. You MUST return exactly the same number of lines as the input."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, # Lower temperature for more consistent results
            max_tokens=2048
        )

    try:
        completion = await call_with_retry(_api_call)
        
        content = completion.choices[0].message.content.strip()
        translated_lines = content.split('\n')
        
        # Cleanup empty lines if any produced by mistake
        translated_lines = [line for line in translated_lines if line.strip()]
        
        if len(translated_lines) != len(texts):
            # print(f"\nWarning: Mismatch in translation count. Sent {len(texts)}, got {len(translated_lines)}. Using fallback line-by-line.")
            # Fallback: Translate one by one if batch fails
            fallback_lines, fallback_failures = await translate_one_by_one(
                client, texts, target_lang, model
            )
            return index, fallback_lines, {
                "batch_error": True,
                "line_fallback_failures": fallback_failures,
            }
            
        return index, translated_lines, {
            "batch_error": False,
            "line_fallback_failures": 0,
        }

    except Exception as e:
        print(f"Translation error in batch {index}: {e}")
        # Try fallback
        fallback_lines, fallback_failures = await translate_one_by_one(
            client, texts, target_lang, model
        )
        return index, fallback_lines, {
            "batch_error": True,
            "line_fallback_failures": fallback_failures,
        }

async def translate_one_by_one(client, texts, target_lang, model):
    results = []
    fallback_failures = 0
    for text in texts:
        async def _single_api_call():
            prompt = f"Translate this subtitle to {target_lang}: \"{text}\". Return ONLY the translation."
            return await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024
            )
            
        try:
            completion = await call_with_retry(_single_api_call)
            results.append(completion.choices[0].message.content.strip())
        except Exception:
            results.append(text)
            fallback_failures += 1
    return results, fallback_failures

def save_srt(original_subs, translated_texts, output_path, bilingual=False):
    for i, sub in enumerate(original_subs):
        if i < len(translated_texts):
            trans_text = translated_texts[i]
            if bilingual:
                # Combine: Translated \n Original
                # Check if original text exists to avoid extra newlines
                if sub.text and sub.text.strip():
                    sub.text = f"{trans_text}\n{sub.text}"
                else:
                    sub.text = trans_text
            else:
                sub.text = trans_text
    original_subs.save(str(output_path), encoding='utf-8')

def save_vtt(original_subs, translated_texts, output_path, bilingual=False):
    # webvtt-py doesn't have a simple 'save' method that modifies in place easily like pysrt
    # We need to rewrite the file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for i, sub in enumerate(original_subs):
            orig_text = sub.text
            if i < len(translated_texts):
                trans_text = translated_texts[i]
            else:
                trans_text = orig_text # Fallback? Or keep original?
            
            if bilingual:
                 final_text = f"{trans_text}\n{orig_text}"
            else:
                 final_text = trans_text
            
            f.write(f"{sub.start} --> {sub.end}\n")
            f.write(f"{final_text}\n\n")

def save_txt(translated_texts, output_path, original_lines=None, bilingual=False):
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, line in enumerate(translated_texts):
            if bilingual and original_lines and i < len(original_lines):
                f.write(f"{line}\n{original_lines[i]}\n")
            else:
                f.write(f"{line}\n")

async def translate_batch_google(texts: List[str], target_lang: str, index: int) -> Tuple[int, List[str], dict]:
    """Translate a batch using Google Translate (runs in executor)."""
    if not texts:
        return index, [], {"batch_error": False, "line_fallback_failures": 0}
    
    loop = asyncio.get_running_loop()
    target_code = get_google_lang_code(target_lang)
    
    def _run_google():
        try:
            # deep-translator handles batching
            translator = GoogleTranslator(source='auto', target=target_code)
            return translator.translate_batch(texts)
        except Exception as e:
            print(f"Google Error batch {index}: {e}")
            # Fallback to returning original texts marked as [Error]
            return texts 
            
    try:
        translated_lines = await loop.run_in_executor(None, _run_google)
        if not translated_lines:
            return index, texts, {
                "batch_error": True,
                "line_fallback_failures": len(texts),
            }
        if len(translated_lines) != len(texts):
            return index, texts, {
                "batch_error": True,
                "line_fallback_failures": len(texts),
            }
        return index, translated_lines, {
            "batch_error": False,
            "line_fallback_failures": 0,
        }
    except Exception as e:
        print(f"Async Google Error batch {index}: {e}")
        return index, texts, {
            "batch_error": True,
            "line_fallback_failures": len(texts),
        }

async def process_file(file_path, args, client):
    file_path = Path(file_path)
    print(f"Processing: {file_path.name}")
    
    # 1. Detect format and read
    ext = file_path.suffix.lower()
    if ext == '.srt':
        parsed_data, raw_obj = read_srt(file_path)
    elif ext == '.vtt':
        parsed_data, raw_obj = read_vtt(file_path)
    elif ext == '.txt':
        parsed_data, raw_obj = read_txt(file_path)
    else:
        print(f"Skipping unsupported file: {file_path}")
        return {
            "file": str(file_path),
            "output": None,
            "status": "failed",
            "total_lines": 0,
            "line_fallback_failures": 0,
            "batch_error_count": 0,
            "service": args.service,
            "model": args.model,
            "target_lang": args.target_lang,
            "error": f"unsupported extension: {ext}",
        }

    texts = [item[2] for item in parsed_data]
    
    # 2. Translate in batches with concurrency and size limits
    translated_texts = [""] * len(texts)
    batch_error_count = 0
    line_fallback_failures = 0
    
    tasks = []
    sem = asyncio.Semaphore(args.concurrency)
    
    # Dynamic batching based on character count
    MAX_CHARS_PER_BATCH = 1500 # Conservative limit to avoid token overflow
    current_batch = []
    current_batch_indices = []
    current_char_count = 0
    
    batches = []
    
    for i, text in enumerate(texts):
        text_len = len(text)
        if len(current_batch) >= args.batch_size or (current_char_count + text_len > MAX_CHARS_PER_BATCH and current_batch):
            batches.append((current_batch, current_batch_indices[0]))
            current_batch = []
            current_batch_indices = []
            current_char_count = 0
            
        current_batch.append(text)
        current_batch_indices.append(i)
        current_char_count += text_len
        
    if current_batch:
        batches.append((current_batch, current_batch_indices[0]))
    
    async def limited_translate_batch(batch, index):
        async with sem:
            # Add small random delay to prevent thundering herd
            await asyncio.sleep(random.uniform(0.1, 0.5)) 
            
            if args.service == "google":
                return await translate_batch_google(batch, args.target_lang, index)
            else:
                return await translate_batch(client, batch, args.target_lang, args.model, index)

    for batch, index in batches:
        tasks.append(limited_translate_batch(batch, index))
    
    # Use tqdm to track progress of tasks
    print(f"Translating {len(texts)} lines in {len(batches)} batches...")
    for f in tqdm.as_completed(tasks, desc="Translating"):
        index, batch_results, meta = await f
        if meta.get("batch_error"):
            batch_error_count += 1
        line_fallback_failures += int(meta.get("line_fallback_failures", 0))
        # Place results in correct position
        for j, res in enumerate(batch_results):
            if index + j < len(translated_texts):
                translated_texts[index + j] = res

    # Guard against sparse fills from unexpected response shape.
    for i, text in enumerate(translated_texts):
        if text == "":
            translated_texts[i] = texts[i]
            line_fallback_failures += 1

    # 3. Save output
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        target_suffix = sanitize_target_lang(args.target_lang)
        suffix = f".{target_suffix}{ext}"
        if args.bilingual:
            suffix = f".{target_suffix}.bilingual{ext}"
        output_path = out_dir / f"{file_path.stem}{suffix}"
    else:
        # Save as filename.lang.ext
        # e.g. movie.en.srt -> movie.en.Chinese.srt
        target_suffix = sanitize_target_lang(args.target_lang)
        suffix = f".{target_suffix}{ext}"
        if args.bilingual:
             suffix = f".{target_suffix}.bilingual{ext}"
        output_path = file_path.parent / f"{file_path.stem}{suffix}"
        
    print(f"Saving to {output_path}")
    if ext == '.srt':
        save_srt(raw_obj, translated_texts, output_path, bilingual=args.bilingual)
    elif ext == '.vtt':
        save_vtt(raw_obj, translated_texts, output_path, bilingual=args.bilingual)
    elif ext == '.txt':
        # Need original lines for bilingual txt
        orig_lines = texts if args.bilingual else None
        save_txt(translated_texts, output_path, original_lines=orig_lines, bilingual=args.bilingual)

    status = "success"
    if line_fallback_failures > 0:
        status = "partial" if line_fallback_failures < len(texts) else "failed"

    return {
        "file": str(file_path),
        "output": str(output_path),
        "status": status,
        "total_lines": len(texts),
        "line_fallback_failures": line_fallback_failures,
        "batch_error_count": batch_error_count,
        "service": args.service,
        "model": args.model,
        "target_lang": args.target_lang,
    }

async def main():
    args = parse_args()
    
    client = None
    if args.service == "llm":
        if not args.model:
            args.model = DEFAULT_LLM_MODEL
        client = get_client(api_key=args.api_key, base_url=args.api_base)
    elif args.service == "ollama":
        if not args.api_base:
            args.api_base = "http://127.0.0.1:11434/v1"
        if not args.api_key:
            args.api_key = "ollama"
        if not args.model:
            args.model = DEFAULT_OLLAMA_MODEL
        client = get_client(api_key=args.api_key, base_url=args.api_base)
    
    input_path = Path(args.input_path)
    summaries = []
    if input_path.is_file():
        summaries.append(await process_file(input_path, args, client))
    elif input_path.is_dir():
        files = list(input_path.glob("*.srt")) + list(input_path.glob("*.vtt")) + list(input_path.glob("*.txt"))
        for f in files:
            summaries.append(await process_file(f, args, client))
    else:
        print(f"Error: {input_path} not found")
        print(json.dumps(
            {"status": "failed", "error": f"{input_path} not found", "results": []},
            ensure_ascii=False,
        ))
        return

    if not summaries:
        overall_status = "failed"
    elif all(s.get("status") == "success" for s in summaries):
        overall_status = "success"
    elif any(s.get("status") == "success" for s in summaries):
        overall_status = "partial"
    else:
        overall_status = "failed"

    print(json.dumps(
        {"status": overall_status, "results": summaries},
        ensure_ascii=False,
    ))

if __name__ == "__main__":
    asyncio.run(main())
