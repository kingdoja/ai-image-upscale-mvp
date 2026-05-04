# 语义高清放大总控框架

日期：2026-05-03  
阶段：MVP v0.18 架构迭代  
适用范围：高清放大工具的图像理解、修复计划、模型路由、质检反馈和后续训练数据闭环

## 1. 总体定位

本项目下一阶段不再只定义为“单模型超分工具”，而是定义为一套可理解、可路由、可评测、可训练回流的图像恢复系统。

gpt-image-2 可借鉴的不是未公开训练细节，而是它体现出的产品/系统思路：先理解文本和图像上下文，再根据约束生成或编辑图像，并把输出质量和风险显式暴露出来。本项目采用本地可控实现，不默认接入外部公共 API，不上传未授权业务图片。

官方参考：

- https://developers.openai.com/api/docs/models/gpt-image-2
- https://developers.openai.com/api/docs/guides/image-generation
- https://developers.openai.com/api/docs/guides/images-vision

## 2. 核心链路

```text
上传图片
-> ImageUnderstandingReport 图像理解
-> UpscalePlan 修复计划
-> RoutingDecision 模型路由
-> 多候选生成
-> QualityBreakdown 质检拆分
-> 人工反馈 / 风险样本导出
-> 后续评测与训练数据治理
```

## 3. 第一阶段边界

- 只做本地规则/轻量视觉分析，不接 gpt-image-2 或其他外部在线生成 API。
- 不从零训练模型，不承诺输出图可直接商用。
- 继续保留 Real-ESRGAN/stub 作为保真主链路，写实/扩散候选作为后续 adapter。
- 用户上传图默认只用于本次推理、评测和本地复盘；进入训练集必须经过授权和数据治理确认。

## 4. 模块职责

| 模块 | 职责 |
|---|---|
| ImageUnderstandingReport | 识别场景、退化类型、主体提示、文字/logo 等风险 |
| UpscalePlan | 决定候选类型、保护区域、增强策略和人工复核 warning |
| RoutingDecision | 把修复计划转成 adapter 候选队列，并记录路由原因 |
| QualityBreakdown | 拆分清晰度、结构、文字/logo、材质、颜色、幻觉风险 |
| Feedback/Risk Export | 将人工反馈映射到失败样本、评测报告和后续训练分桶 |

## 5. 总控可追溯性

正式评测不能只保存最终图片，还要保存当时的总控口径。后续规则变化后，同一张图的解释和路由可能变化，因此所有摘要必须暴露版本：

| 字段 | 说明 |
|---|---|
| `controller_version` | 图像理解规则版本，当前为 `semantic-controller-v0.10.0` |
| `policy_version` | 路由和修复计划版本 |
| `model_version` | 实际候选图使用的模型版本 |
| `quality_policy_version` | 后续质量评分策略版本，当前预留 |

## 6. 模型能力注册

总控层不直接假设“写实模型一定更好”，而是根据模型能力做路由：

| 候选 | 优势 | 限制 | 幻觉风险 | 默认策略 |
|---|---|---|---|---|
| `faithful` | 结构稳定、低幻觉、适合产品图 | 缺失细节恢复有限 | 低 | 默认主候选 |
| `sharpened` | 快、本地可用、兜底稳定 | 不是真实模型增强，可能过锐化 | 低 | 演示/失败兜底 |
| `realistic` | 写实细节和材质增强更强 | 慢、可能生成假纹理/错文字 | 高 | 只作为复核候选 |

## 7. 区域保护结构

当前 `protected_regions` 继续保留简单字符串，兼容前端展示；同时新增结构化区域摘要，为 OCR、Logo 检测和主体分割预留接口：

```text
type: text / logo / product_edge / instrument_panel
bbox: [x, y, w, h] 或空
confidence: 0.0-1.0
source: scene_rule / vision_detector / graphic_mark_detector / tesseract_ocr / ocr / logo_detector / segmentation / user_hint
policy: preserve / paste_back / manual_review
```

v0.3 使用 `layout_heuristic` 为营销/电商场景生成本地布局保护框，让 `bbox` 从空值变成可用于展示和报告导出的区域坐标。v0.4 新增 `vision_detector`，通过本地图像明暗区域检测识别疑似 logo/文字块；它仍不是 OCR，不能声称识别了真实文字内容。v0.10 将彩色 badge/source 拆为 `graphic_mark_detector`，并新增独立 `logo_detector` adapter 边界。后续 OCR、Logo 检测和主体分割接入后，`source` 才能升级为 `ocr`、`logo_detector` 或 `segmentation`。

当前布局启发式：

| 场景 | 文字保护框 | Logo 保护框 |
|---|---|---|
| `marketing` | 下方约 45% 区域 | 左上约 25% x 18% |
| `ecommerce` | 下方约 38% 区域 | 左上约 25% x 18% |
| 缺失图片 | 保留风险，但 `bbox=null` | 保留风险，但 `bbox=null` |

v0.4 本地区域检测：

| 检测来源 | 能力 | 边界 |
|---|---|---|
| `vision_detector` | 在营销/电商图中检测高对比暗色块，优先替代布局启发式框 | 只能定位疑似区域，不能读取文字、不能确认品牌 Logo |
| `graphic_mark_detector` | 在暗色块 detector 未找到 Logo 时，补充高饱和彩色 badge/logo 候选 | 只是图形标记启发式，不识别品牌身份 |

v0.5 外部 OCR/Logo detector 协议：

| 配置 | 默认值 | 说明 |
|---|---|---|
| `UPSCALE_REGION_DETECTOR_BACKEND` | `local` | `local` 使用内置轻量检测；`external` 先调用本地外部 detector，失败后回退 `local` |
| `UPSCALE_REGION_DETECTOR_COMMAND` | 空 | 受信任的本地命令，不默认上传第三方公共服务 |
| `UPSCALE_REGION_DETECTOR_TIMEOUT_SECONDS` | `30` | 外部 detector 超时时间 |

外部命令协议为 `<command> <image_path> <scene>`。命令也可以使用 `{input}` 和 `{scene}` 占位符。stdout 必须输出 JSON：

```json
{
  "regions": [
    {
      "type": "text",
      "bbox": [12, 34, 120, 28],
      "confidence": 0.91,
      "source": "ocr",
      "policy": "preserve"
    },
    {
      "type": "logo",
      "bbox": [40, 20, 80, 35],
      "confidence": 0.88,
      "source": "logo_detector",
      "policy": "preserve"
    }
  ]
}
```

解析失败、命令失败、超时或没有返回有效区域时，总控层自动回退本地 detector 与 layout fallback。这样第一期仍保持本地可控，同时为后续接 PaddleOCR、Tesseract、企业 Logo detector 或主体分割留下稳定 adapter 边界。

v0.6 内置 Tesseract CLI adapter：

| 配置 | 默认值 | 说明 |
|---|---|---|
| `UPSCALE_REGION_DETECTOR_BACKEND` | `local` | 设置为 `tesseract` 时优先调用本机 Tesseract OCR |
| `UPSCALE_TESSERACT_COMMAND` | `tesseract` | Tesseract 可执行命令；可替换为绝对路径或带 `{input}` 的自定义命令 |
| `UPSCALE_REGION_DETECTOR_TIMEOUT_SECONDS` | `30` | OCR 超时时间 |

Tesseract adapter 不引入新的 Python 依赖，不上传图片，不识别 Logo；它调用本机 CLI 输出 TSV，聚合有效 word boxes 为 `source=tesseract_ocr` 的 `text` 保护区域。未安装 Tesseract、命令失败、TSV 无有效文字或超时时，仍回退到现有本地 detector。

v0.7 detector fusion：

当 `tesseract` backend 返回文字区域时，总控不再只信任 OCR 单一路径，而是继续运行本地 detector 补齐缺失类型。合并规则为“高优先级 detector 在前，按 `type` 去重”：

```text
tesseract_ocr text
local vision_detector logo/text
-> keep tesseract_ocr text
-> add vision_detector logo if OCR did not already return logo
```

这样电商/营销图可以同时获得更准的文字框和本地图像启发式 Logo 框；如果 OCR 没有输出文字，则沿用完整本地 detector fallback。

v0.9 colored badge/logo heuristic：

本地 detector 新增高饱和色块扫描，用于识别营销图、电商图中的红色圆形贴纸、彩色促销 badge、明显品牌色块等非黑色 Logo 候选。触发条件保持保守：

- 只在 `marketing` / `ecommerce` 场景启用。
- 必须是面积适中的高饱和色块；纯白产品图、全暗背景、覆盖大半张图的彩色背景不触发。
- 返回 `source=graphic_mark_detector`，避免和暗色块 `vision_detector` 混在一起。

v0.10 Logo detector adapter/source split：

Logo 检测被拆成独立 adapter 边界，不再继续把所有 Logo 相关启发式塞进通用区域检测。新增配置：

| 配置 | 默认值 | 说明 |
|---|---|---|
| `UPSCALE_LOGO_DETECTOR_BACKEND` | `local` | 设置为 `external` 时调用受信任的本地 Logo detector 命令 |
| `UPSCALE_LOGO_DETECTOR_COMMAND` | 空 | 命令协议沿用 `<command> <image_path> <scene>`，stdout 输出 JSON |

外部 Logo detector 只接收 `type=logo` 的区域，未提供 `source` 时默认写为 `logo_detector`。融合优先级为高置信外部/专用检测在前，再补齐本地 detector：

```text
tesseract_ocr text
external logo_detector logo
local vision_detector / graphic_mark_detector missing types
-> keep tesseract_ocr text
-> keep logo_detector logo
-> fall back to local detector when logo command fails or returns no valid logo
```

v0.11 Local Logo baseline adapter：

为避免“接口有了但不可评测”，项目新增一个 Pillow-only 的本地 baseline 命令：

```text
tools/logo_detector_baseline.py <image_path> <scene>
```

它输出与外部 Logo detector 协议一致的 JSON，只用于本地 smoke/eval，不作为真实品牌识别模型。当前策略保守地寻找营销/电商图中心区域的高对比图形标记，`source=logo_detector_baseline`。v0.17 增加密集子标记收缩：当大候选框明显包住包装/标签噪声时，优先定位内部更紧致的图形标记区域。它的价值是给未来替换成企业 Logo detector、轻量分类模型或分割模型提供可运行对照，而不是宣称已经完成 Logo 身份识别。

v0.12 Bbox-quality evaluation：

评测集支持在 `annotations.json` 中补充可选 `expected_bboxes`：

```json
{
  "expected_bboxes": {
    "text": [100, 80, 1045, 1370],
    "logo": [103, 80, 1045, 530]
  }
}
```

评测报告新增 `bbox_ious`、`bbox_matches`、`bbox_misses`，默认 IoU 阈值为 `0.3`。这让 detector 评估从“有没有报 text/logo”升级到“区域是否大致框对”。例如 v0.11 baseline 能把 Logo 类型召回提升到 `4/4`，但 bbox 匹配仍只有 `4/8`，说明它是有用的 baseline，而不是可直接商用的 Logo 定位器。
- 只在本地暗色 logo detector 未找到 logo 时补充。

这不是品牌身份识别，只是“需要保护的图形标识区域”定位。真实 Logo 语义仍需要后续模板匹配或专用 detector。

## 8. 候选降级说明

计划候选不等于实际产出候选。系统必须同时解释：

| 字段 | 说明 |
|---|---|
| `candidate_types` | 总控计划候选 |
| `executed_candidate_types` | 实际生成候选 |
| `skipped_candidate_types` | 未生成候选 |
| `skip_reasons` | 未生成原因，如 backend 未启用 |

这样当 `realistic` 后端未启用时，用户能看到“计划有写实候选，但当前环境未生成”，不会误解为系统漏处理。

## 9. Semantic Manifest

总控结果必须在任务处理时固化，避免评测报告随着代码版本、detector 规则或原图文件变化而漂移。

```text
process_job
-> build_semantic_context
-> run model adapters
-> record executed/skipped candidates
-> write storage/manifests/{job_id}.json
```

读取策略：

| 场景 | 策略 |
|---|---|
| job detail | 优先读 `storage/manifests/{job_id}.json` |
| batch report | 优先读 manifest，不重新跑 detector |
| manifest 缺失 | 回退动态构建，用于兼容旧任务 |
| 重新处理任务 | 覆盖写入最新 manifest |

## 10. Region Eval Harness

Detector 继续迭代前，必须先能量化“漏检文字、漏检 Logo、误报区域”。项目新增本地评测集目录：

```text
datasets/region-eval/
  annotations.json
  samples/
```

标注格式只记录本地评测所需的最小信息：

```json
{
  "file": "samples/marketing-text-logo.png",
  "scene": "marketing",
  "expected_regions": ["text", "logo"],
  "review_required": true,
  "notes": "Approved marketing sample with visible text and logo."
}
```

评测脚本：

```powershell
python tools/evaluate_region_detector.py `
  --annotations datasets/region-eval/annotations.json `
  --backend local `
  --markdown-output reports/region-detector-eval.md `
  --csv-output reports/region-detector-eval.csv
```

输出指标包括：

| 指标 | 说明 |
|---|---|
| `missed_text` / `missed_logo` | 标注期望存在，但 detector 未返回 |
| `false_positive_text` / `false_positive_logo` | 标注不期望存在，但 detector 返回 |
| `detector_sources` | 每个区域来自 `vision_detector`、`graphic_mark_detector`、`tesseract_ocr` 或外部 adapter |
| `protected_regions` | detector 返回的 bbox，便于人工复盘 |
| `expected_bboxes` | 人工粗标的期望 bbox，格式为 `type:x,y,w,h` |
| `bbox_ious` / `bbox_matches` / `bbox_misses` | 按类型计算 bbox IoU 和定位是否达标 |

该 harness 只读本地样张，不上传第三方服务。后续是否接 PaddleOCR、Logo detector 或分割模型，应优先参考这个报告，而不是只靠单张 demo 感觉。v0.11 起，harness 支持 `--logo-detector-backend external` 和 `--logo-detector-command`，可量化专用 Logo adapter 与 Tesseract OCR 的融合效果。

## 11. 数据治理状态

用户上传图默认不进入训练集。每个 job detail 暴露数据治理摘要：

```text
usage_scope: local_inference_and_evaluation
training_state: not_approved_for_training
retention_policy: local_project_storage
requires_approval_for_training: true
```

后续如果进入训练平台，状态才能从 `not_approved_for_training` 升级为 `training_candidate` 或 `training_approved`。

## 12. 总控决策矩阵

| 场景 | 默认风险 | 默认候选 | 复核要求 |
|---|---|---|---|
| `product` | 低 | `faithful + sharpened` | 结果用于初稿仍建议人工抽检 |
| `marketing` | 文字/logo 风险 | `faithful + realistic(review-only)` | 必须复核文字、Logo、版式 |
| `ecommerce` | 型号/参数风险 | `faithful + realistic(review-only)` | 必须复核参数、型号、详情文字 |
| `other` | 不确定 | `faithful + sharpened` | 根据结果风险人工判断 |

## 13. 长期演进

P0：规则版语义总控底座，当前已落地。  
P0.5：布局启发式区域保护，当前已落地。  
P0.6：本地区域检测和 manifest 固化，当前已落地。  
P0.7：外部 OCR/logo detector 命令协议，当前已落地为可选本地 adapter。  
P0.8：Tesseract CLI OCR adapter，当前已落地为可选本地文字区域 detector。  
P0.9：Detector fusion，当前已落地为 Tesseract 文字框 + 本地 Logo/缺失类型补齐。  
P0.10：Region eval harness，当前已落地为本地样张标注、指标统计和 Markdown/CSV 报告。  
P0.11：Colored badge/logo heuristic，当前已落地为高饱和图形标识保护区域补充。  
P0.12：Logo detector adapter/source split，当前已落地为独立外部 Logo 命令入口与 `graphic_mark_detector` source 拆分。  
P0.13：Local Logo baseline adapter，当前已落地为 Pillow-only 本地命令和 Tesseract+Logo fusion 评测报告。  
P0.14：Bbox-quality evaluation，当前已落地为 `expected_bboxes` 标注、IoU 指标和定位匹配报告。  
P0.15：Bbox localization rate reporting，当前已落地为整体和按类型的 bbox match rate。  
P0.16：Confidence-aware detector fusion，当前已落地为同类型区域置信度择优，并保留 Tesseract OCR 文本优先。  
P0.17：Region eval dataset coverage，当前已加入 text-only、plain product negative 和 synthetic packaging fixtures，并收紧 product 场景 detector 边界。  
P0.18：Logo false-positive suppression，当前已加入 precision/recall 指标、baseline 背景对比过滤和文字横条误报抑制。  
P0.19：Logo dense-submark bbox refinement，当前已加入大候选框内密集子标记收缩，使 Tesseract+Logo baseline 的 `bbox_match_rate_logo` 达到 `1.0`。  
P0.20：Guided Tesseract text OCR pass，当前已加入基于本地 Logo/图形框的裁剪 OCR 候选，使 Tesseract+Logo baseline 的 `bbox_match_rate_text` 提升到 `0.857`。  
P0.21：Badge text fallback，当前已在 Tesseract 漏读短文字时，把大型彩色 badge/图形标记降级为 `badge_text_fallback` 文本保护区，使 Tesseract+Logo baseline 的 `bbox_match_rate_text` 提升到 `1.0`。  
P1：接入真实 OCR/logo/主体分割，提升风险区域识别精度。  
P2：接入 DiffBIR/SUPIR/SeeSR 等写实候选 adapter。  
P3：建设固定 Benchmark、退化模拟器和训练白名单。  
P4：在授权数据上训练或微调九号产品域保真超分模型。

## 14. v0.13/v0.14 Evaluation And Fusion Notes

- Region evaluation now separates type recall from localization quality with `bbox_match_rate`, `bbox_match_rate_text`, and `bbox_match_rate_logo`.
- Same-type detector fusion is confidence-aware: a lower-confidence external Logo adapter must not overwrite a stronger local Logo region.
- `source=tesseract_ocr` text regions remain preferred for text boundaries because OCR text boxes carry stronger semantic intent than generic visual blocks.
- A higher-confidence external Logo detector can still replace local fallback regions, preserving the adapter path for a future real local Logo model.
- v0.18 adds guided OCR candidates: when a local Logo/graphic region exists, the text detector can crop and rescan that neighborhood before selecting the best text bbox. This keeps the implementation local and dependency-light while improving coarse text localization.
- v0.21 adds `badge_text_fallback`: if Tesseract still returns no text and a large colored badge/graphic mark exists, the detector records that graphic box as a manual-review text protection region. This is a protection signal, not a claim that OCR read the literal words.
