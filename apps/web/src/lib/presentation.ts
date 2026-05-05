import type { ResultRead } from "./api";

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: "排队中",
    running: "处理中",
    completed: "已完成",
    failed: "失败"
  };
  return labels[status] ?? status;
}

export function modeLabel(mode: string): string {
  const labels: Record<string, string> = {
    faithful: "保真模式",
    realistic: "写实增强模式",
    both: "保真 + 写实"
  };
  return labels[mode] ?? mode;
}

export function resultTypeLabel(type: ResultRead["type"]): string {
  const labels: Record<ResultRead["type"], string> = {
    faithful: "保真基线",
    realistic: "写实增强",
    sharpened: "已停用结果",
    swinir: "SwinIR",
    hat: "HAT",
    material_guard: "已停用候选"
  };
  return labels[type];
}

export function resultDisplayLabel(result: ResultRead): string {
  const modelName = result.model_name.toLowerCase();
  if (result.type === "faithful" && modelName === "realesrgan") {
    return "Real-ESRGAN";
  }
  if (result.type === "swinir") {
    return "SwinIR";
  }
  if (result.type === "hat") {
    return "HAT";
  }
  return resultTypeLabel(result.type);
}

export function riskLabel(risk: ResultRead["risk_level"]): string {
  const labels: Record<ResultRead["risk_level"], string> = {
    low: "低风险",
    medium: "需人工审核",
    high: "高风险"
  };
  return labels[risk];
}

export function warningLabel(warning: string): string {
  const normalized = warning.toLowerCase();
  if (normalized.includes("stub_adapter_used") || normalized.includes("stub")) {
    return "部分候选图为演示兜底或历史结果，正式评审请优先查看模型名称为 Real-ESRGAN 的结果。";
  }
  if (
    normalized.includes("realesrgan") ||
    normalized.includes("model") ||
    normalized.includes("inference") ||
    normalized.includes("adapter")
  ) {
    return "真实模型处理失败，系统返回了兜底预览结果。";
  }
  if (
    normalized.includes("logo") ||
    normalized.includes("text") ||
    normalized.includes("文本") ||
    normalized.includes("型号") ||
    normalized.includes("仪表盘")
  ) {
    return "Logo、型号、文本或仪表盘区域建议人工复核。";
  }
  return warning;
}

export function semanticLabel(value: string): string {
  const labels: Record<string, string> = {
    low_resolution_input: "低分辨率输入",
    compressed_source: "压缩来源",
    standard_resolution_input: "标准分辨率输入",
    text_region_requires_review: "文本区域需复核",
    logo_region_requires_review: "Logo 区域需复核",
    manual_review_required: "需要人工复核",
    generic_product_subject: "产品主体",
    marketing_layout: "营销版式",
    possible_brand_text: "可能包含品牌文字",
    ecommerce_detail_image: "电商详情图",
    possible_product_specs: "可能包含型号参数",
    general_image_subject: "通用图片主体",
    text: "文本",
    logo: "Logo",
    conservative_preserve_structure: "保守增强，优先保护结构",
    balanced_detail_enhancement: "平衡增强，提升细节",
    protected_risk_regions: "已保护高风险区域",
    realistic_candidate_is_review_only: "写实候选仅供复核",
    "requested_mode:faithful": "按保真模式路由",
    "requested_mode:realistic": "按写实模式请求，先保留保真候选",
    "requested_mode:both": "按双候选模式路由",
    "policy:conservative_preserve_structure": "策略：保守保护结构",
    "policy:balanced_detail_enhancement": "策略：平衡细节增强",
    scene_rule: "场景规则",
    layout_heuristic: "布局启发式",
    vision_detector: "本地区域检测",
    graphic_mark_detector: "彩色图形标记检测",
    tesseract_ocr: "Tesseract OCR",
    preserve: "保真保护",
    inference_only: "仅本次推理",
    local_inference_and_evaluation: "本地推理与评测",
    not_approved_for_training: "未批准训练使用",
    local_project_storage: "本地项目存储",
    backend_disabled_or_not_configured: "后端未启用或未配置",
    candidate_not_generated: "候选未生成",
    material_texture_fidelity: "材质纹理保真",
    color_stability: "颜色稳定",
    transformer_sr_baseline: "Transformer 超分基线",
    strong_transformer_sr_baseline: "强 Transformer 超分基线",
    detail_reconstruction_comparison: "细节重建对比",
    fine_detail_comparison: "细节对比",
    optional_runtime_not_bundled: "可选运行时未内置",
    requires_configured_weights: "需要配置权重"
  };
  return labels[value] ?? value;
}
