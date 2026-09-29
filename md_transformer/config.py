from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"缺少配置文件：{path}，请复制 .env.example 为 .env 并填写 Key")
    values = dotenv_values(path, encoding="utf-8-sig", interpolate=False)
    url = (values.get("SURYA_INFERENCE_URL") or "").strip().rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"请在 {path} 中填写有效的 SURYA_INFERENCE_URL（http/https 地址）")
    url = url if url.endswith("/v1") else url + "/v1"
    key = (values.get("VLLM_API_KEY") or "").strip()
    if not key or key in ("填写你的key", "填写你的 key"):
        raise ValueError(f"请在 {path} 中填写真实的 VLLM_API_KEY")
    try:
        concurrency = int(values.get("CONCURRENCY", "4"))
        requests_per_worker = int(values.get("SURYA_INFERENCE_PARALLEL", "8"))
    except (TypeError, ValueError):
        raise ValueError(".env 中 CONCURRENCY 和 SURYA_INFERENCE_PARALLEL 必须是正整数") from None
    if concurrency < 1 or requests_per_worker < 1:
        raise ValueError(".env 中 CONCURRENCY 和 SURYA_INFERENCE_PARALLEL 必须是正整数")
    mode = values.get("MARKER_MODE") or "balanced"
    if mode not in ("balanced", "fast"):
        raise ValueError("MARKER_MODE 必须为 balanced 或 fast")
    return dict(surya_url=url, api_key=key, concurrency=concurrency, requests_per_worker=requests_per_worker, mode=mode)


def check_service(url: str, key: str) -> None:
    # Validate connectivity and authentication once, before dispatching PDFs.
    try:
        with httpx.Client(timeout=10, trust_env=False, headers={"Authorization": f"Bearer {key}"}) as client:
            for endpoint in (url.removesuffix("/v1") + "/health", url + "/models"):
                response = client.get(endpoint)
                if response.status_code in (401, 403):
                    raise ValueError("Surya 认证失败，请检查 .env 中的 VLLM_API_KEY")
                if response.status_code != 200:
                    raise ValueError(f"Surya 服务检查失败（HTTP {response.status_code}）：{endpoint}")
    except httpx.RequestError:
        raise ValueError(f"无法连接 Surya：{url}，请检查服务、端口和网络") from None
