# MD-transformer-v2

This project vendors Marker source and adds recursive PDF conversion, external Surya vLLM configuration, fixed concurrency, and custom Markdown/image output.

## Setup

```powershell
Copy-Item .env.example .env
# edit .env and set VLLM_API_KEY
.\scripts\setup.ps1
```

## Run

```powershell
.\.venv\Scripts\python.exe -m md_transformer E:\data\pdf-root
```

Outputs stay beside each PDF as `<name>.md` and `<name>_images`. Run statistics are printed only in the terminal; no report JSON file is written. Marker source is included in this repository; `E:\work\marker` is not used at runtime.


The setup script installs the CUDA 12.6 PyTorch build for NVIDIA GPUs (the current machine was verified with an RTX 4060 Laptop GPU).


Optional output root (input directory structure is preserved):

```powershell
.\.venv\Scripts\python.exe -m md_transformer E:\data\pdf-root --output-root E:\data\markdown
```

Without `--output-root`, each PDF writes beside itself. With it, for example `E:\data\pdf-root\a\b.pdf` writes to `E:\data\markdown\a\b.md` and `E:\data\markdown\a\b_images\`.

Concurrency is configured in `.env`:

```env
CONCURRENCY=4
SURYA_INFERENCE_PARALLEL=10
```

配置固定读取项目根目录 `.env`，OCR 地址、Key 和并发值以该文件为准，不再回退到 localhost 或继承的同名环境变量。支持 Windows UTF-8 BOM。
缺少配置、非法并发值、服务不可达或认证失败时，批处理启动前报错；不会将所有 PDF 逐个尝试。
固定最多同时处理 4 个 PDF，完成一个立即处理下一个。不会自动探测或升降并发；OOM 和其他错误记录为文件失败，继续处理其余文件，不自动重试。终端统计使用 concurrency 表示配置并发数。

SURYA_INFERENCE_PARALLEL 控制每个 worker 的 OCR 请求并发，默认 10。4 个 worker 合计最多约 40 个 OCR 请求；它不是服务端的调度参数。

