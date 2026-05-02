# AI 产品图高清放大工具

一个面向电商、广告和营销场景的 AI 图片高清放大 MVP。它可以将低清商品图、详情页图片和营销素材放大为更清晰的 2x/4x 候选结果，并通过对比、反馈和评测记录沉淀后续模型优化数据。

## Demo 视频

2 分 20 秒 MVP 演示，覆盖上传图片、创建任务、查看结果、批量处理和导出评测材料。

[观看 MVP Demo 演示视频](assets/ai-upscale-mvp-demo.mp4)

## 项目亮点

- **产品场景清晰**：围绕商品图、营销图、详情页图的清晰度提升，而不是泛泛的图片处理 demo。
- **端到端链路完整**：上传、创建任务、异步推理、结果对比、反馈评估和导出都已跑通。
- **可从 demo 走向评测**：支持单图和批量处理，可导出评测报告、失败样本和高风险样本清单。
- **工程上可替换模型**：默认 stub 便于本地开发，也可切换 Real-ESRGAN 保真模式继续验证真实效果。
- **保留商业使用边界**：Logo、文字、型号和材质细节保留人工复核入口，避免把 AI 结果直接当作最终商用图。

当前阶段：**MVP v0.1 工程闭环已完成，前端已优化为工作台版本**。真实业务效果评估需要后续使用授权产品/营销素材单独执行，本阶段已按计划跳过授权素材真实评测。

## 1. 项目目标

MVP 需要验证三件事：

1. 团队用户是否高频需要高清放大能力。
2. 基于成熟开源模型组合，是否能让 80% 普通产品/营销图清晰度明显提升。
3. 是否能沉淀失败样本、用户反馈和模型接入经验，为后续自研训练平台做准备。

MVP 不追求一次性训练专属模型，而是优先跑通完整产品链路：

```text
上传图片 -> 创建任务 -> 异步推理 -> 生成候选结果 -> 用户对比 -> 提交反馈 -> 数据沉淀
```

## 2. 文档说明

项目方案、评审材料、spec、plan、验收报告默认保留在本地 `docs/` 和 `tests/acceptance/` 中，不纳入 Git 跟踪，也不推送到 GitHub。

## 3. 推荐执行顺序

1. 先实现 stub 模型链路，不依赖 GPU 跑通端到端流程。
2. 后端任务、存储、反馈闭环稳定后，再接保真模型。
3. 保真模式稳定后，再接写实扩散模型。
4. 用本地授权素材做小样本冒烟测试。
5. 根据评测结果决定是否进入自研训练平台阶段。

## 4. MVP 技术架构

推荐技术栈：

| 层级 | 推荐 |
|---|---|
| 前端 | Next.js + TypeScript |
| 后端 API | FastAPI |
| 任务队列 | Redis + RQ |
| 数据库 | PostgreSQL |
| 图片存储 | 本地文件系统或 MinIO，生产可替换对象存储 |
| 推理服务 | Python + PyTorch |
| 模型适配 | Stub -> Real-ESRGAN/HAT/SwinIR -> DiffBIR/SUPIR/SeeSR |
| 部署 | Docker Compose 起步，GPU worker 独立扩展 |

一句话架构：

```text
Web 前端提交任务，FastAPI 保存任务和图片，Redis/RQ 调度 GPU worker，worker 通过统一模型 adapter 生成候选结果，用户在前端对比并反馈。
```

## 5. 本阶段不做

MVP 阶段明确不做：

- 不从零训练模型。
- 不做视频超分。
- 不做公开 C 端产品。
- 不做 8x 作为首期验收指标。
- 不把私有图片上传到第三方公共 API。
- 不承诺写实模式输出可直接商用，核心营销图仍需人工审核。

## 6. 文档归档规则

- 项目方案、spec、plan、验收文档：本地 `docs/`，不提交 Git。
- 本地评测报告：本地 `tests/acceptance/`，不提交 Git。
- 可复用工程脚本：`scripts/` 或非敏感 `tools/`。

## 7. 当前进度与下一步

已完成：

- 后端 FastAPI 基础接口、任务创建、状态查询、反馈接口。
- SQLite/SQLAlchemy 数据模型与本地文件存储。
- Pillow stub 推理链路，可在无 GPU、无模型权重时本地开发。
- Real-ESRGAN ncnn-vulkan 本地模型安装、健康检查、Python adapter 调用。
- worker 级真实 Real-ESRGAN 集成测试：创建任务、调用真实 CLI、生成 4x `faithful` 结果并入库。
- 前端 Next.js 上传、状态展示、结果展示、反馈表单。
- Demo 产品化体验：原图预览、自动刷新、结果打开/下载、复制结果 ID、风险提示、反馈成功提示。
- 批量上传、批量结果 ZIP 下载、六维评估打分、批量评测报告导出、失败/高风险样本训练清单导出。
- Docker Compose 配置校验。

当前收尾状态：

1. MVP 工程闭环已完成，可作为团队试用和演示基础版本。
2. 前端工作台已包含上传、批量、最近任务、结果对比、反馈评测和导出入口。
3. 代码已通过前端 lint/build 验证。
4. 授权素材真实评测暂不执行；后续需要业务验收时再补充 10 张授权产品/营销图评测。
5. 后续如进入正式评审，建议用 Real-ESRGAN 保真模式跑小样本评测，生成本地评测报告和风险样本清单。

10 张冒烟评测 runner：

```powershell
New-Item -ItemType Directory -Force -Path test-tmp\smoke-storage | Out-Null
$env:STORAGE_ROOT=(Resolve-Path 'test-tmp\smoke-storage').Path
$env:DATABASE_URL='sqlite:///./test-tmp/smoke-acceptance.db'
$env:ENQUEUE_JOBS='false'
$env:UPSCALE_PROCESS_INLINE='true'
.\.venv\Scripts\python.exe tools\run_smoke_acceptance.py `
  --samples-dir <your-10-image-folder> `
  --output tests\acceptance\smoke-report.md `
  --limit 10
```

如果要用本机 Real-ESRGAN 保真模式跑冒烟评测，先设置：

```powershell
$env:UPSCALE_FAITHFUL_BACKEND='realesrgan'
$env:REALESRGAN_EXECUTABLE=(Resolve-Path 'models\realesrgan\realesrgan-ncnn-vulkan.exe').Path
$env:REALESRGAN_MODEL_PATH=(Resolve-Path 'models\realesrgan\models').Path
$env:REALESRGAN_MODEL='realesrgan-x4plus'
```

## 8. 本地开发命令

本地 Demo 推荐使用启动脚本：

```powershell
.\scripts\start_api_demo.ps1
.\scripts\start_web_demo.ps1
```

如果只验证工程链路、不跑真实 Real-ESRGAN：

```powershell
.\scripts\start_api_demo.ps1 -Backend stub
```

首次安装 Python 依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\apps\api
```

运行后端测试时使用项目虚拟环境，并把 pytest 临时目录放到项目内：

```powershell
cd apps/api
New-Item -ItemType Directory -Force -Path test-tmp | Out-Null
$env:TMP=(Resolve-Path 'test-tmp').Path
$env:TEMP=$env:TMP
..\..\.venv\Scripts\python.exe -m pytest -v --basetemp test-tmp\pytest
```

前端：

```powershell
cd apps/web
npm install
npm run lint
npm run build
```

Docker 配置校验：

```powershell
docker compose -f infra/docker-compose.yml config
```

## 9. 接入真实保真模型

默认开发模式使用 Pillow stub adapter，不需要 GPU 或模型权重。

要切换 Real-ESRGAN 保真模式，配置：

```powershell
$env:UPSCALE_FAITHFUL_BACKEND="realesrgan"
$env:REALESRGAN_EXECUTABLE="D:\models\upscale\realesrgan\realesrgan-ncnn-vulkan.exe"
$env:REALESRGAN_MODEL_PATH="D:\models\upscale\realesrgan\models"
$env:REALESRGAN_MODEL="realesrgan-x4plus"
```

API 会按以下格式调用外部命令：

```powershell
realesrgan-ncnn-vulkan.exe -i <input> -o <output> -s 4 -m <models目录> -n realesrgan-x4plus
```

如果真实模型未配置或执行失败，worker 会把错误写入任务 warning；MVP 仍保留 stub/sharpened 候选图作为兜底。

本机已加入真实 Real-ESRGAN worker 集成测试。模型文件存在时会执行真实 CLI；模型文件不存在时测试自动跳过：

```powershell
cd apps/api
New-Item -ItemType Directory -Force -Path test-tmp | Out-Null
$env:TMP=(Resolve-Path 'test-tmp').Path
$env:TEMP=$env:TMP
..\..\.venv\Scripts\python.exe -m pytest tests\test_worker.py::test_worker_completes_real_realesrgan_job_when_local_model_is_available -v --basetemp test-tmp\pytest
```

接入前可以先运行健康检查：

```powershell
.\scripts\check_realesrgan.ps1 `
  -Executable "D:\models\upscale\realesrgan\realesrgan-ncnn-vulkan.exe" `
  -Model "realesrgan-x4plus" `
  -Scale 4
```

也可以用安装脚本自动下载并检查：

```powershell
.\scripts\install_realesrgan.ps1 -Proxy "http://127.0.0.1:7897"
```
