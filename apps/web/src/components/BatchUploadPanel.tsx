import { Settings, Upload } from "lucide-react";
import { useMemo, useState } from "react";
import { createBatch, type BatchCreateResponse, type ModelStatus } from "../lib/api";
import { CANDIDATE_OPTIONS, DEFAULT_CANDIDATES, orderedCandidates, type SelectableCandidate } from "../lib/candidates";
import { formatFileSize } from "../lib/presentation";
import { ModelStatusPanel } from "./ModelStatusPanel";

type Props = {
  onCreated: (batch: BatchCreateResponse) => void;
  onError: (message: string) => void;
  modelStatuses: ModelStatus[];
  modelStatusLoading: boolean;
  modelStatusError: string | null;
  onRefreshModelStatuses: () => void;
};

export function BatchUploadPanel({
  onCreated,
  onError,
  modelStatuses,
  modelStatusLoading,
  modelStatusError,
  onRefreshModelStatuses
}: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [scale, setScale] = useState("4");
  const [mode, setMode] = useState("faithful");
  const [scene, setScene] = useState("product");
  const [candidates, setCandidates] = useState<SelectableCandidate[]>(DEFAULT_CANDIDATES);
  const [loading, setLoading] = useState(false);
  const [showModelStatus, setShowModelStatus] = useState(false);

  const validationMessage = useMemo(() => {
    if (files.length === 0) {
      return "请选择 2-20 张图片。";
    }
    if (files.length < 2) {
      return "批量处理至少选择 2 张图片；单张图片请使用上传工作台。";
    }
    if (files.length > 20) {
      return "单批最多支持 20 张图片，请拆分后再提交。";
    }
    return "";
  }, [files.length]);

  async function submit() {
    if (validationMessage || loading) {
      return;
    }
    const form = new FormData();
    files.forEach((file) => form.append("images", file));
    form.append("scale", scale);
    form.append("mode", mode);
    form.append("scene", scene);
    orderedCandidates(candidates).forEach((candidate) => form.append("candidates", candidate));
    setLoading(true);
    try {
      onCreated(await createBatch(form));
    } catch {
      onError("批量任务创建失败，请确认后端服务是否启动");
    } finally {
      setLoading(false);
    }
  }

  function toggleCandidate(candidate: SelectableCandidate) {
    setCandidates((current) => {
      if (current.includes(candidate)) {
        return current.filter((item) => item !== candidate);
      }
      return orderedCandidates([...current, candidate]);
    });
  }

  return (
    <section>
      <h2 className="section-title">批量处理</h2>
      <p className="subtle">适合一次处理 2-20 张公开样本或已授权素材。每张图会生成独立任务，方便单独查看、重试和反馈。</p>
      <div className="field">
        <label htmlFor="batch-images">图片文件</label>
        <input
          id="batch-images"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
        />
      </div>
      {files.length > 0 ? (
        <div className="batch-file-list">
          <div className="batch-file-summary">
            <strong>{files.length} 张图片</strong>
            <span>{files.reduce((total, file) => total + file.size, 0) ? formatFileSize(files.reduce((total, file) => total + file.size, 0)) : "0 B"}</span>
          </div>
          {files.map((file) => (
            <div className="batch-file-row" key={`${file.name}-${file.size}-${file.lastModified}`}>
              <span>{file.name}</span>
              <span>{formatFileSize(file.size)}</span>
            </div>
          ))}
        </div>
      ) : null}
      {validationMessage ? <p className="form-warning">{validationMessage}</p> : null}
      <div className="field">
        <label>倍率</label>
        <div className="segments">
          {["2", "4"].map((value) => (
            <button key={value} className={`segment ${scale === value ? "active" : ""}`} onClick={() => setScale(value)} type="button">
              {value}x
            </button>
          ))}
        </div>
      </div>
      <div className="field">
        <label>模式</label>
        <div className="segments">
          {[
            ["faithful", "保真"],
            ["realistic", "写实"],
            ["both", "同时"]
          ].map(([value, label]) => (
            <button key={value} className={`segment ${mode === value ? "active" : ""}`} onClick={() => setMode(value)} type="button">
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="field">
        <label htmlFor="batch-scene">场景</label>
        <select id="batch-scene" value={scene} onChange={(event) => setScene(event.target.value)}>
          <option value="product">产品图</option>
          <option value="marketing">营销图</option>
          <option value="ecommerce">电商详情页</option>
          <option value="other">其他</option>
        </select>
      </div>
      <div className="field">
        <div className="field-row">
          <label>生成模型</label>
          <button
            type="button"
            className={`link-button model-status-toggle ${showModelStatus ? "active" : ""}`}
            onClick={() => setShowModelStatus((current) => !current)}
            aria-expanded={showModelStatus}
          >
            <Settings size={14} />
            {showModelStatus ? "收回" : "设置"}
          </button>
        </div>
        <div className="segments">
          {CANDIDATE_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`segment ${candidates.includes(option.value) ? "active" : ""}`}
              onClick={() => toggleCandidate(option.value)}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="inline-actions">
          <button type="button" className="link-button" onClick={() => setCandidates(CANDIDATE_OPTIONS.map((option) => option.value))}>
            全选
          </button>
          <button type="button" className="link-button" onClick={() => setCandidates(DEFAULT_CANDIDATES)}>
            默认
          </button>
        </div>
        {showModelStatus ? (
          <div className="model-status-inline">
            <ModelStatusPanel
              models={modelStatuses}
              loading={modelStatusLoading}
              error={modelStatusError}
              onRefresh={onRefreshModelStatuses}
              compact
            />
          </div>
        ) : null}
      </div>
      <button className="primary" disabled={Boolean(validationMessage) || loading || candidates.length === 0} onClick={submit} type="button">
        <Upload size={16} /> {loading ? "创建中" : "创建批量任务"}
      </button>
    </section>
  );
}
