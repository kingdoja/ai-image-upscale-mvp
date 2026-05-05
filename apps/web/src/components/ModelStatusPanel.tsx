import { Cpu, RefreshCw } from "lucide-react";
import type { ModelStatus } from "../lib/api";

type Props = {
  models: ModelStatus[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  compact?: boolean;
};

const statusLabels: Record<ModelStatus["status"], string> = {
  ready: "已就绪",
  demo: "演示模式",
  disabled: "未启用",
  missing_config: "缺配置"
};

export function ModelStatusPanel({ models, loading, error, onRefresh, compact = false }: Props) {
  return (
    <section className={`model-status-panel ${compact ? "compact" : ""}`}>
      {compact ? (
        <div className="model-status-compact-heading">
          <span>模型配置状态</span>
          <button type="button" className="link-button" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={14} />
            刷新
          </button>
        </div>
      ) : (
        <div className="panel-heading">
          <div>
            <h2 className="section-title">模型配置状态</h2>
            <p className="subtle">确认当前生成链路是否接上真实权重。</p>
          </div>
          <button type="button" className="secondary small-button" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={14} />
            刷新
          </button>
        </div>
      )}
      {error ? <p className="form-warning">{error}</p> : null}
      <div className="model-status-grid">
        {models.map((model) => (
          <article className="model-status-card" key={model.id}>
            <div className="model-status-title">
              <Cpu size={16} />
              <strong>{model.label}</strong>
              <span className={`model-status-badge model-status-${model.status}`}>{statusLabels[model.status]}</span>
            </div>
            <div className="model-status-meta">
              <span>backend: {model.backend}</span>
              <span>{model.detail}</span>
            </div>
          </article>
        ))}
        {loading && models.length === 0 ? (
          <article className="model-status-card">
            <div className="model-status-title">
              <Cpu size={16} />
              <strong>正在读取配置</strong>
            </div>
            <div className="model-status-meta">
              <span>等待后端返回模型状态</span>
            </div>
          </article>
        ) : null}
      </div>
    </section>
  );
}
