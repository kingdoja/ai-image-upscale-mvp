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
    faithful: "保真结果",
    realistic: "写实增强",
    sharpened: "锐化兜底"
  };
  return labels[type];
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
    return "部分候选图为演示兜底或锐化结果，正式评审请优先查看模型名称为 Real-ESRGAN 的结果。";
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
    normalized.includes("文字") ||
    normalized.includes("型号") ||
    normalized.includes("仪表盘")
  ) {
    return "Logo、型号、文字或仪表盘区域建议人工复核。";
  }
  return warning;
}
