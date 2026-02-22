import os
import sys
import json
import subprocess
import argparse
import shutil
from pathlib import Path

# Configuration
SKILL_DIR = Path(__file__).parent
ENGINE_DIR = SKILL_DIR / "engine"
WHISPER_REPO = "https://github.com/ggml-org/whisper.cpp.git"
WHISPER_DIR = ENGINE_DIR / "whisper.cpp"
MODEL = "base"  # Default model


class CommandError(RuntimeError):
    pass


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and raise structured error for caller fallback."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, check=False, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise CommandError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def check_dependencies():
    """Check required tools. Build requires either make or cmake."""
    required_base = ["git", "ffmpeg"]
    missing = [tool for tool in required_base if not shutil.which(tool)]

    has_make = bool(shutil.which("make"))
    has_cmake = bool(shutil.which("cmake"))
    if not (has_make or has_cmake):
        missing.append("make/cmake")

    has_cpp = bool(shutil.which("c++") or shutil.which("clang++") or shutil.which("g++"))
    if not has_cpp:
        missing.append("c++ compiler")

    if missing:
        raise CommandError(
            "Missing required tools: "
            + ", ".join(missing)
            + ". Install example: brew install ffmpeg git cmake"
        )


def find_whisper_executable():
    candidates = [
        WHISPER_DIR / "build" / "bin" / "whisper-cli",
        WHISPER_DIR / "main",
        WHISPER_DIR / "build" / "main",
    ]
    for exe in candidates:
        if exe.exists():
            return exe
    return None


def build_whisper():
    has_make = bool(shutil.which("make"))
    has_cmake = bool(shutil.which("cmake"))

    if has_make:
        try:
            run_command(["make", "-j"], cwd=WHISPER_DIR, check=True)
            return
        except CommandError as e:
            print(f"make build failed, will try cmake fallback.\n{e}")

    if has_cmake:
        run_command(["cmake", "-B", "build"], cwd=WHISPER_DIR, check=True)
        run_command(["cmake", "--build", "build", "--config", "Release"], cwd=WHISPER_DIR, check=True)
        return

    raise CommandError("No usable builder found (make/cmake).")


def setup_whisper():
    """Clone and build whisper.cpp."""
    if not ENGINE_DIR.exists():
        ENGINE_DIR.mkdir(parents=True)

    if not WHISPER_DIR.exists():
        print("Cloning whisper.cpp...")
        run_command(["git", "clone", WHISPER_REPO], cwd=ENGINE_DIR, check=True)

    executable = find_whisper_executable()
    if not executable:
        print("Building whisper.cpp...")
        build_whisper()
        executable = find_whisper_executable()
        if not executable:
            raise CommandError("Could not find whisper executable after build.")

    model_path = WHISPER_DIR / "models" / f"ggml-{MODEL}.bin"
    if not model_path.exists():
        print(f"Downloading model {MODEL}...")
        script = WHISPER_DIR / "models" / "download-ggml-model.sh"
        run_command(["bash", str(script), MODEL], cwd=WHISPER_DIR, check=True)
    return executable, model_path


def convert_audio(input_path):
    """Convert audio/video to 16kHz 16-bit mono WAV."""
    input_path = Path(input_path).absolute()
    output_path = input_path.with_suffix(".wav_16k.wav")

    if output_path.exists():
        return output_path

    print(f"Converting {input_path} to compatible WAV...")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    result = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise CommandError(f"FFmpeg conversion failed:\n{result.stderr.decode(errors='ignore')}")
    return output_path


def locate_output_file(wav_file: Path, output_format: str):
    ext = f".{output_format}"
    candidates = [
        wav_file.parent / f"{wav_file.name}{ext}",
        wav_file.parent / f"{wav_file.stem}{ext}",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def transcribe(input_file, output_format="txt", print_transcript=False):
    """Run transcription and return structured summary."""
    try:
        check_dependencies()
        executable, model_path = setup_whisper()

        wav_file = convert_audio(input_file)
        print(f"Transcribing {wav_file}...")

        cmd = [str(executable), "-m", str(model_path), "-f", str(wav_file)]
        if output_format == "vtt":
            cmd.append("--output-vtt")
        elif output_format == "srt":
            cmd.append("--output-srt")
        elif output_format == "lrc":
            cmd.append("--output-lrc")
        else:
            cmd.append("--output-txt")

        run_command(cmd, cwd=WHISPER_DIR, check=True)
        output_file = locate_output_file(wav_file, output_format)
        status = "success" if output_file else "partial"
        summary = {
            "status": status,
            "input": str(Path(input_file).absolute()),
            "wav_file": str(wav_file),
            "model": MODEL,
            "format": output_format,
            "output_file": str(output_file) if output_file else None,
            "engine_dir": str(WHISPER_DIR),
        }

        if output_file and print_transcript:
            with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
                print("\n--- Transcript ---\n")
                print(f.read())
                print("\n------------------\n")
        return summary
    except Exception as e:
        return {
            "status": "failed",
            "input": str(Path(input_file).absolute()),
            "model": MODEL,
            "format": output_format,
            "error": str(e),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio/video using whisper.cpp")
    parser.add_argument("file", help="Path to audio/video file")
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model to use (tiny, base, small, medium, large)",
    )
    parser.add_argument(
        "--format",
        default="txt",
        choices=["txt", "vtt", "srt", "lrc"],
        help="Output format (txt, vtt, srt, lrc)",
    )
    parser.add_argument(
        "--print-transcript",
        action="store_true",
        help="Print transcript content to stdout after transcription",
    )
    args = parser.parse_args()

    if args.model:
        MODEL = args.model

    result = transcribe(args.file, output_format=args.format, print_transcript=args.print_transcript)
    print(json.dumps(result, ensure_ascii=False))
    if result.get("status") == "failed":
        sys.exit(1)
