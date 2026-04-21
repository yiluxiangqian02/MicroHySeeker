from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


API_BASE_URL = "https://mineru.net"
UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/v4/file-urls/batch"
BATCH_RESULT_ENDPOINT = f"{API_BASE_URL}/api/v4/extract-results/batch/{{batch_id}}"
DEFAULT_MODEL_VERSION = "vlm"
DEFAULT_LANGUAGE = "en"
DEFAULT_POLL_INTERVAL = 10
DEFAULT_MAX_WAIT = 1800
DEFAULT_TIMEOUT = 120
MAX_BATCH_SIZE = 200
MAX_OUTPUT_NAME_LENGTH = 80
INVALID_PATH_CHARS = '<>:"/\\|?*'


@dataclass(slots=True)
class AppConfig:
    token: str
    input_dir: Path
    output_dir: Path
    cache_dir: Path
    model_version: str
    language: str | None
    enable_formula: bool
    enable_table: bool
    is_ocr: bool
    recursive: bool
    poll_interval_seconds: int
    max_wait_seconds: int
    request_timeout_seconds: int
    use_env_proxy: bool


@dataclass(slots=True)
class SubmittedFile:
    source_path: Path
    upload_name: str
    output_name: str
    data_id: str
    upload_url: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch parse local PDF files with MinerU API and extract results to folders."
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="Optional explicit PDF file list. If omitted, all PDFs under --input-dir are used.",
    )
    parser.add_argument("--input-dir", help="Directory containing PDF files.")
    parser.add_argument("--output-dir", help="Directory for extracted results.")
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Whether to recursively scan --input-dir for PDFs.",
    )
    parser.add_argument("--model-version", choices=["pipeline", "vlm", "MinerU-HTML"])
    parser.add_argument("--language", help="MinerU language value, such as en or ch.")
    parser.add_argument(
        "--enable-formula",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable formula recognition.",
    )
    parser.add_argument(
        "--enable-table",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable table recognition.",
    )
    parser.add_argument(
        "--is-ocr",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable OCR for uploaded files.",
    )
    parser.add_argument("--poll-interval", type=int, help="Polling interval in seconds.")
    parser.add_argument("--max-wait", type=int, help="Maximum wait time in seconds.")
    parser.add_argument("--timeout", type=int, help="HTTP request timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir / ".env")

    args = parse_args()
    config = build_config(script_dir, args)
    pdf_paths = collect_pdf_paths(config.input_dir, config.recursive, args.files)
    if not pdf_paths:
        raise SystemExit(f"No PDF files found under: {config.input_dir}")

    print(f"Found {len(pdf_paths)} PDF file(s) to process.")
    submitted_files = build_submitted_files(pdf_paths)

    session = requests.Session()
    # Some environments inject proxy settings that break signed OSS upload URLs.
    # Default to direct connection unless explicitly enabled via env.
    session.trust_env = config.use_env_proxy
    session.headers.update(
        {
            "Authorization": f"Bearer {config.token}",
            "Accept": "application/json",
        }
    )

    summaries: list[dict[str, Any]] = []
    for batch_index, batch in enumerate(chunked(submitted_files, MAX_BATCH_SIZE), start=1):
        print(f"Processing batch {batch_index} with {len(batch)} file(s).")
        batch_id = create_batch(session, config, batch)
        upload_files(session, config, batch)
        results = poll_batch_results(session, config, batch_id, batch)
        batch_summaries = download_and_extract_results(session, config, batch_id, batch, results)
        summaries.extend(batch_summaries)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = config.output_dir / "manifest.json"
    manifest = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(summaries),
        "results": summaries,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    success_count = sum(1 for item in summaries if item["state"] == "done")
    failed_count = len(summaries) - success_count
    print(f"Completed. Success: {success_count}, failed: {failed_count}.")
    print(f"Output directory: {config.output_dir}")
    print(f"Manifest: {manifest_path}")
    return 0 if failed_count == 0 else 1


def build_config(script_dir: Path, args: argparse.Namespace) -> AppConfig:
    token = read_required_env("MINERU_API_TOKEN")
    input_dir = resolve_path(script_dir, args.input_dir or os.getenv("MINERU_INPUT_DIR", "./input"))
    output_dir = resolve_path(script_dir, args.output_dir or os.getenv("MINERU_OUTPUT_DIR", "./output"))
    cache_dir = resolve_path(script_dir, os.getenv("MINERU_CACHE_DIR", "./.cache"))

    model_version = args.model_version or os.getenv("MINERU_MODEL_VERSION", DEFAULT_MODEL_VERSION)
    language = args.language or os.getenv("MINERU_LANGUAGE", DEFAULT_LANGUAGE)
    recursive = (
        args.recursive
        if args.recursive is not None
        else parse_bool_env("MINERU_RECURSIVE", default=True)
    )
    enable_formula = (
        args.enable_formula
        if args.enable_formula is not None
        else parse_bool_env("MINERU_ENABLE_FORMULA", default=True)
    )
    enable_table = (
        args.enable_table
        if args.enable_table is not None
        else parse_bool_env("MINERU_ENABLE_TABLE", default=True)
    )
    is_ocr = args.is_ocr if args.is_ocr is not None else parse_bool_env("MINERU_IS_OCR", default=False)
    poll_interval_seconds = args.poll_interval or read_int_env(
        "MINERU_POLL_INTERVAL_SECONDS", DEFAULT_POLL_INTERVAL
    )
    max_wait_seconds = args.max_wait or read_int_env("MINERU_MAX_WAIT_SECONDS", DEFAULT_MAX_WAIT)
    request_timeout_seconds = args.timeout or read_int_env(
        "MINERU_REQUEST_TIMEOUT_SECONDS", DEFAULT_TIMEOUT
    )
    use_env_proxy = parse_bool_env("MINERU_USE_ENV_PROXY", default=False)

    return AppConfig(
        token=token,
        input_dir=input_dir,
        output_dir=output_dir,
        cache_dir=cache_dir,
        model_version=model_version,
        language=language.strip() if language else None,
        enable_formula=enable_formula,
        enable_table=enable_table,
        is_ocr=is_ocr,
        recursive=recursive,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        request_timeout_seconds=request_timeout_seconds,
        use_env_proxy=use_env_proxy,
    )


def read_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env var: {name}. Fill it in MinerU/.env first.")
    return value


def parse_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"Env var {name} must be true or false.")


def read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"Env var {name} must be an integer.") from exc


def resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def collect_pdf_paths(input_dir: Path, recursive: bool, files: list[str] | None) -> list[Path]:
    if files:
        pdf_paths = [Path(file).resolve() for file in files]
        missing = [path for path in pdf_paths if not path.exists()]
        if missing:
            missing_text = ", ".join(str(path) for path in missing)
            raise SystemExit(f"These files do not exist: {missing_text}")
        return pdf_paths

    if not input_dir.exists():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(path.resolve() for path in input_dir.glob(pattern) if path.is_file())


def build_submitted_files(pdf_paths: list[Path]) -> list[SubmittedFile]:
    used_upload_names: set[str] = set()
    used_output_names: set[str] = set()
    submitted_files: list[SubmittedFile] = []

    for path in pdf_paths:
        upload_name = make_unique_upload_name(path, used_upload_names)
        output_name = make_unique_output_name(path.stem, used_output_names)
        data_id = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:16]
        submitted_files.append(
            SubmittedFile(
                source_path=path,
                upload_name=upload_name,
                output_name=output_name,
                data_id=data_id,
            )
        )
    return submitted_files


def make_unique_upload_name(path: Path, used_names: set[str]) -> str:
    candidate = path.name
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    suffix = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    candidate = f"{path.stem}__{suffix}{path.suffix}"
    used_names.add(candidate)
    return candidate


def make_unique_output_name(stem: str, used_names: set[str]) -> str:
    safe_stem = sanitize_path_name(stem) or "paper"
    safe_stem = shorten_output_name(safe_stem, MAX_OUTPUT_NAME_LENGTH)
    candidate = safe_stem
    index = 2
    while candidate in used_names:
        suffix = f"_{index}"
        base_max = max(1, MAX_OUTPUT_NAME_LENGTH - len(suffix))
        candidate = f"{safe_stem[:base_max]}{suffix}"
        index += 1
    used_names.add(candidate)
    return candidate


def shorten_output_name(name: str, max_length: int) -> str:
    if len(name) <= max_length:
        return name
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    keep = max(1, max_length - 9)
    return f"{name[:keep]}_{digest}"


def sanitize_path_name(name: str) -> str:
    return "".join("_" if char in INVALID_PATH_CHARS else char for char in name).strip(" .")


def chunked(items: list[SubmittedFile], size: int) -> list[list[SubmittedFile]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def create_batch(session: requests.Session, config: AppConfig, batch: list[SubmittedFile]) -> str:
    payload: dict[str, Any] = {
        "files": [
            {
                "name": item.upload_name,
                "data_id": item.data_id,
                "is_ocr": config.is_ocr,
            }
            for item in batch
        ],
        "model_version": config.model_version,
        "enable_formula": config.enable_formula,
        "enable_table": config.enable_table,
    }
    if config.language:
        payload["language"] = config.language

    response = session.post(
        UPLOAD_ENDPOINT,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=config.request_timeout_seconds,
    )
    response.raise_for_status()
    result = response.json()
    assert_api_success(result, "Failed to create upload batch")

    data = result["data"]
    batch_id = data["batch_id"]
    file_urls = data["file_urls"]
    if len(file_urls) != len(batch):
        raise SystemExit("MinerU returned a mismatched number of upload URLs.")

    for item, upload_url in zip(batch, file_urls):
        item.upload_url = upload_url
    print(f"Batch created: {batch_id}")
    return batch_id


def upload_files(session: requests.Session, config: AppConfig, batch: list[SubmittedFile]) -> None:
    for item in batch:
        print(f"Uploading: {item.source_path.name}")
        with item.source_path.open("rb") as handle:
            response = session.put(item.upload_url, data=handle, timeout=config.request_timeout_seconds)
        if response.status_code not in {200, 201}:
            raise SystemExit(
                f"Upload failed for {item.source_path} with status code {response.status_code}."
            )


def poll_batch_results(
    session: requests.Session,
    config: AppConfig,
    batch_id: str,
    batch: list[SubmittedFile],
) -> dict[str, dict[str, Any]]:
    started_at = time.time()
    expected_names = {item.upload_name for item in batch}
    batch_url = BATCH_RESULT_ENDPOINT.format(batch_id=batch_id)

    while True:
        response = session.get(batch_url, timeout=config.request_timeout_seconds)
        response.raise_for_status()
        result = response.json()
        assert_api_success(result, "Failed to query batch results")

        raw_results = result.get("data", {}).get("extract_result", [])
        normalized_results = normalize_batch_results(raw_results)
        current_states = {
            file_name: item.get("state", "unknown")
            for file_name, item in normalized_results.items()
            if file_name in expected_names
        }
        if current_states:
            state_text = ", ".join(f"{name}={state}" for name, state in sorted(current_states.items()))
            print(f"Current states: {state_text}")

        if expected_names and expected_names.issubset(normalized_results.keys()):
            if all(normalized_results[name].get("state") in {"done", "failed"} for name in expected_names):
                return normalized_results

        if time.time() - started_at > config.max_wait_seconds:
            raise SystemExit(f"Polling timed out for batch_id={batch_id}")

        time.sleep(config.poll_interval_seconds)


def normalize_batch_results(raw_results: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw_results, dict):
        raw_items = [raw_results]
    else:
        raw_items = raw_results or []
    normalized: dict[str, dict[str, Any]] = {}
    for item in raw_items:
        file_name = item.get("file_name")
        if file_name:
            normalized[file_name] = item
    return normalized


def download_and_extract_results(
    session: requests.Session,
    config: AppConfig,
    batch_id: str,
    batch: list[SubmittedFile],
    results: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []
    for item in batch:
        result = results.get(item.upload_name, {})
        state = result.get("state", "unknown")
        summary: dict[str, Any] = {
            "source_pdf": str(item.source_path),
            "upload_name": item.upload_name,
            "output_name": item.output_name,
            "batch_id": batch_id,
            "state": state,
            "error": result.get("err_msg", ""),
            "output_dir": "",
            "markdown_path": "",
        }

        if state != "done":
            print(f"Parse failed: {item.source_path.name}. Reason: {summary['error'] or state}")
            summaries.append(summary)
            continue

        zip_url = result.get("full_zip_url")
        if not zip_url:
            summary["state"] = "failed"
            summary["error"] = "MinerU did not return full_zip_url."
            summaries.append(summary)
            continue

        target_dir = config.output_dir / item.output_name
        markdown_path = extract_zip_to_folder(
            session=session,
            config=config,
            zip_url=zip_url,
            target_dir=target_dir,
            output_name=item.output_name,
        )
        summary["output_dir"] = str(target_dir)
        summary["markdown_path"] = str(markdown_path) if markdown_path else ""
        summary["download_url"] = zip_url
        summaries.append(summary)
        print(f"Extracted to: {target_dir}")

    return summaries


def extract_zip_to_folder(
    session: requests.Session,
    config: AppConfig,
    zip_url: str,
    target_dir: Path,
    output_name: str,
) -> Path | None:
    with tempfile.TemporaryDirectory(dir=config.cache_dir) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        zip_path = temp_dir / "result.zip"
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with session.get(zip_url, stream=True, timeout=config.request_timeout_seconds) as response:
            response.raise_for_status()
            with zip_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)

        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)

        replace_directory(target_dir, extract_dir)
        return copy_named_markdown(target_dir, output_name)


def replace_directory(target_dir: Path, source_dir: Path) -> None:
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)


def copy_named_markdown(target_dir: Path, output_name: str) -> Path | None:
    markdown_candidates = list(target_dir.rglob("full.md"))
    if not markdown_candidates:
        return None
    target_markdown = target_dir / f"{output_name}.md"
    shutil.copy2(markdown_candidates[0], target_markdown)
    return target_markdown


def assert_api_success(result: dict[str, Any], message: str) -> None:
    if result.get("code") not in {0, "0"}:
        detail = result.get("msg") or result.get("message") or "unknown error"
        raise SystemExit(f"{message}: {detail}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as exc:
        response = exc.response
        if response is not None:
            detail = response.text[:500]
            print(f"HTTP request failed: {response.status_code} {detail}", file=sys.stderr)
        else:
            print(f"HTTP request failed: {exc}", file=sys.stderr)
        raise
