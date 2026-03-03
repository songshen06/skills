import sys
import json
import glob
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
SUPPORTED_INPUT_EXTS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".wma",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
}


class CommandError(RuntimeError):
    def __init__(self, message=None, cmd=None, returncode=None, stdout="", stderr=""):
        self.cmd = cmd or []
        self.returncode = returncode
        self.stdout = stdout or ""
        self.stderr = stderr or ""
        if message is None:
            message = (
                f"command failed ({returncode}): {' '.join(self.cmd)}\n"
                f"stdout:\n{self.stdout}\n"
                f"stderr:\n{self.stderr}"
            )
        super().__init__(message)


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and raise structured error for caller fallback."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, check=False, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise CommandError(cmd=cmd, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
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


def convert_audio(input_path, output_dir=None):
    """Convert audio/video to 16kHz 16-bit mono WAV."""
    input_path = Path(input_path).absolute()
    if output_dir:
        output_dir = Path(output_dir).absolute()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}.wav_16k.wav"
    else:
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
        raise CommandError(
            cmd=cmd,
            returncode=result.returncode,
            stdout="",
            stderr=f"FFmpeg conversion failed:\n{result.stderr.decode(errors='ignore')}",
        )
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


def classify_command_error(error: CommandError):
    text = f"{error.stderr}\n{error.stdout}".lower()
    if "ffmpeg conversion failed" in text and "no such file or directory" in text:
        return "input_not_found"
    if "ffmpeg conversion failed" in text or "invalid data found" in text:
        return "audio_conversion_failed"
    if "ggml_metal_buffer_init" in text or "failed to allocate buffer" in text:
        return "gpu_memory_error"
    if "no such file or directory" in text and "whisper" in " ".join(error.cmd).lower():
        return "engine_not_found"
    if "failed to open" in text and "ggml-" in text:
        return "model_not_found_or_invalid"
    if "permission denied" in text:
        return "permission_denied"
    return "command_failed"


def expected_output_from_base(output_base: Path, output_format: str):
    return output_base.parent / f"{output_base.name}.{output_format}"


def normalize_output_base(output_file: str, output_format: str):
    output_path = Path(output_file).absolute()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == f".{output_format}":
        return output_path.with_suffix("")
    return output_path


def collect_input_files(inputs, recursive=False):
    files = []
    seen = set()
    for raw in inputs:
        expanded = glob.glob(raw, recursive=recursive)
        candidates = expanded if expanded else [raw]
        for item in candidates:
            path = Path(item)
            if path.is_dir():
                iterator = path.rglob("*") if recursive else path.glob("*")
                for child in sorted(iterator):
                    if child.is_file() and child.suffix.lower() in SUPPORTED_INPUT_EXTS:
                        key = str(child.absolute())
                        if key not in seen:
                            seen.add(key)
                            files.append(child.absolute())
            else:
                key = str(path.absolute())
                if key not in seen:
                    seen.add(key)
                    files.append(path.absolute())
    return files


def transcribe(
    input_file,
    output_format="txt",
    print_transcript=False,
    output_dir=None,
    output_file=None,
    language=None,
    translate=False,
    force_cpu=False,
    force_gpu=False,
    executable=None,
    model_path=None,
):
    """Run transcription and return structured summary."""
    try:
        if force_cpu and force_gpu:
            raise ValueError("Only one of force_cpu/force_gpu can be true.")
        if output_dir and output_file:
            raise ValueError("Only one of output_dir/output_file can be set.")
        if executable is None or model_path is None:
            check_dependencies()
            executable, model_path = setup_whisper()

        wav_file = convert_audio(input_file, output_dir=output_dir)
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

        if language:
            cmd.extend(["--language", language])
        if translate:
            cmd.append("--translate")
        if force_cpu:
            cmd.append("--no-gpu")

        output_base = None
        if output_file:
            output_base = normalize_output_base(output_file, output_format)
            cmd.extend(["--output-file", str(output_base)])
        elif output_dir:
            output_base = Path(output_dir).absolute() / wav_file.name
            cmd.extend(["--output-file", str(output_base)])

        try:
            run_command(cmd, cwd=WHISPER_DIR, check=True)
        except CommandError as e:
            # Some macOS environments fail Metal allocation; fallback to CPU.
            err = f"{e.stderr}\n{e.stdout}"
            if (not force_gpu and not force_cpu) and (
                "ggml_metal_buffer_init" in err or "failed to allocate buffer" in err
            ):
                print("GPU init failed, retrying with CPU (--no-gpu)...")
                run_command(cmd + ["--no-gpu"], cwd=WHISPER_DIR, check=True)
            else:
                raise
        if output_base:
            output_file = expected_output_from_base(output_base, output_format)
            if not output_file.exists():
                output_file = None
        else:
            output_file = locate_output_file(wav_file, output_format)
        status = "success" if output_file else "partial"
        summary = {
            "status": status,
            "input": str(Path(input_file).absolute()),
            "wav_file": str(wav_file),
            "model": MODEL,
            "format": output_format,
            "language": language or "default",
            "translated_to_english": bool(translate),
            "force_cpu": bool(force_cpu),
            "force_gpu": bool(force_gpu),
            "output_file": str(output_file) if output_file else None,
            "engine_dir": str(WHISPER_DIR),
        }

        if output_file and print_transcript:
            with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
                print("\n--- Transcript ---\n")
                print(f.read())
                print("\n------------------\n")
        return summary
    except ValueError as e:
        return {
            "status": "failed",
            "input": str(Path(input_file).absolute()),
            "model": MODEL,
            "format": output_format,
            "error_code": "invalid_arguments",
            "error_message": str(e),
        }
    except CommandError as e:
        return {
            "status": "failed",
            "input": str(Path(input_file).absolute()),
            "model": MODEL,
            "format": output_format,
            "error_code": classify_command_error(e),
            "error_message": str(e),
            "command": e.cmd,
            "returncode": e.returncode,
            "stderr_tail": "\n".join(e.stderr.splitlines()[-20:]),
        }
    except Exception as e:
        return {
            "status": "failed",
            "input": str(Path(input_file).absolute()),
            "model": MODEL,
            "format": output_format,
            "error_code": "unexpected_error",
            "error_message": str(e),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio/video using whisper.cpp")
    parser.add_argument("file", nargs="+", help="Path(s) to audio/video file, directory, or glob pattern")
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
    parser.add_argument(
        "--output-dir",
        help="Directory for generated WAV and transcript outputs",
    )
    parser.add_argument(
        "--output-file",
        help="Exact output file path (single input only). Extension is optional.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Language code for transcription (e.g. zh, en, auto)",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Translate source language to English",
    )
    parser.add_argument(
        "--force-cpu",
        action="store_true",
        help="Disable GPU and force CPU inference",
    )
    parser.add_argument(
        "--force-gpu",
        action="store_true",
        help="Force GPU inference (disable auto CPU fallback)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When input includes directories/globs, scan recursively",
    )
    args = parser.parse_args()

    if args.model:
        MODEL = args.model

    input_files = collect_input_files(args.file, recursive=args.recursive)

    if len(input_files) == 1:
        result = transcribe(
            str(input_files[0]),
            output_format=args.format,
            print_transcript=args.print_transcript,
            output_dir=args.output_dir,
            output_file=args.output_file,
            language=args.language,
            translate=args.translate,
            force_cpu=args.force_cpu,
            force_gpu=args.force_gpu,
        )
        print(json.dumps(result, ensure_ascii=False))
        if result.get("status") == "failed":
            sys.exit(1)
        sys.exit(0)

    if args.output_file:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_code": "invalid_arguments",
                    "error_message": "--output-file only supports single input",
                    "total": len(input_files),
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    check_dependencies()
    executable, model_path = setup_whisper()

    results = []
    failed = 0
    for path in input_files:
        result = transcribe(
            str(path),
            output_format=args.format,
            print_transcript=args.print_transcript,
            output_dir=args.output_dir,
            output_file=None,
            language=args.language,
            translate=args.translate,
            force_cpu=args.force_cpu,
            force_gpu=args.force_gpu,
            executable=executable,
            model_path=model_path,
        )
        if result.get("status") == "failed":
            failed += 1
        results.append(result)

    summary = {
        "status": "success" if failed == 0 else ("partial" if failed < len(results) else "failed"),
        "total": len(results),
        "failed": failed,
        "succeeded": len(results) - failed,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False))
    if failed > 0:
        sys.exit(1)
