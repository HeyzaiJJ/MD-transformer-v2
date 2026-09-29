from __future__ import annotations

import gc
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

_model_refs = None
Job = tuple[Path, Path]


def _init_worker(surya_url: str, api_key: str, mode: str, requests_per_worker: int) -> None:
    # Set before importing Surya: its settings are instantiated at import time.
    os.environ["SURYA_INFERENCE_PARALLEL"] = str(requests_per_worker)
    os.environ["SURYA_INFERENCE_URL"] = surya_url
    os.environ["VLLM_API_KEY"] = api_key
    os.environ["SURYA_INFERENCE_BACKEND"] = "vllm"
    os.environ["SURYA_INFERENCE_AUTOSTART"] = "false"
    os.environ["TORCH_DEVICE"] = "cuda" if mode == "balanced" and os.environ.get("MD_TRANSFORMER_LOCAL_GPU") == "1" else "cpu"
    os.environ["IN_STREAMLIT"] = "true"
    global _model_refs
    from marker.models import create_model_dict
    _model_refs = create_model_dict(device=os.environ["TORCH_DEVICE"])


def _convert_one(input_pdf: str, output_pdf: str, mode: str) -> tuple[str, int]:
    from marker.converters.pdf import PdfConverter
    from .output import save_markdown_output
    converter = PdfConverter(
        artifact_dict=_model_refs,
        config={"mode": mode, "output_format": "markdown", "extract_images": True, "pdftext_workers": 1},
        renderer="marker.renderers.markdown.MarkdownRenderer",
    )
    rendered = converter(input_pdf)
    save_markdown_output(rendered, Path(output_pdf))
    pages = converter.page_count or 0
    del rendered, converter
    gc.collect()
    return input_pdf, pages


def is_oom(error: BaseException) -> bool:
    text = f"{type(error).__name__}: {error}".lower()
    return any(x in text for x in ("cuda out of memory", "out of memory", "outofmemoryerror", "resource exhausted"))


def run_batch(jobs: list[Job], *, mode: str, concurrency: int, surya_url: str, api_key: str, requests_per_worker: int):
    succeeded: list[Job] = []
    failed: dict[Path, str] = {}
    oom_count = 0
    if not jobs:
        return succeeded, failed, oom_count
    with ProcessPoolExecutor(max_workers=concurrency, initializer=_init_worker,
                             initargs=(surya_url, api_key, mode, requests_per_worker)) as pool:
        futures = {pool.submit(_convert_one, str(source), str(target), mode): (source, target)
                   for source, target in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                future.result()
                succeeded.append(job)
            except Exception as exc:
                failed[job[0]] = f"{type(exc).__name__}: {exc}"
                oom_count += int(is_oom(exc))
    return succeeded, failed, oom_count
