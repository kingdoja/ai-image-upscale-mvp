import { ImagePlus, Settings, SlidersHorizontal, Upload } from "lucide-react";
import { useState } from "react";
import type { PreviewImage } from "../app/page";
import { createJob, type CreateJobResponse, type ModelStatus } from "../lib/api";
import { CANDIDATE_OPTIONS, DEFAULT_CANDIDATES, orderedCandidates, type SelectableCandidate } from "../lib/candidates";
import { formatFileSize } from "../lib/presentation";
import { ModelStatusPanel } from "./ModelStatusPanel";

type Props = {
  preview: PreviewImage | null;
  onPreviewChanged: (preview: PreviewImage | null) => void;
  onCreated: (job: CreateJobResponse) => void;
  onError: (message: string) => void;
  modelStatuses: ModelStatus[];
  modelStatusLoading: boolean;
  modelStatusError: string | null;
  onRefreshModelStatuses: () => void;
};

export function Uploader({
  preview,
  onPreviewChanged,
  onCreated,
  onError,
  modelStatuses,
  modelStatusLoading,
  modelStatusError,
  onRefreshModelStatuses
}: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [scale, setScale] = useState("4");
  const [mode, setMode] = useState("both");
  const [scene, setScene] = useState("product");
  const [candidates, setCandidates] = useState<SelectableCandidate[]>(DEFAULT_CANDIDATES);
  const [loading, setLoading] = useState(false);
  const [showModelStatus, setShowModelStatus] = useState(false);

  function selectFile(nextFile: File | null) {
    setFile(nextFile);
    if (!nextFile) {
      onPreviewChanged(null);
      return;
    }
    onPreviewChanged({
      url: URL.createObjectURL(nextFile),
      name: nextFile.name,
      size: nextFile.size
    });
  }

  async function submit() {
    if (!file) {
      return;
    }
    const form = new FormData();
    form.append("image", file);
    form.append("scale", scale);
    form.append("mode", mode);
    form.append("scene", scene);
    orderedCandidates(candidates).forEach((candidate) => form.append("candidates", candidate));
    setLoading(true);
    try {
      onCreated(await createJob(form));
    } catch {
      onError("后端服务未连接，请先启动 FastAPI 服务");
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
    <section className="upload-panel">
      <div className="panel-heading">
        <div>
          <h2 className="section-title">上传图片</h2>
          <p className="subtle">支持 JPG、PNG、WebP。建议先使用已授权、非敏感素材。</p>
        </div>
        <span className="panel-icon">
          <Upload size={18} />
        </span>
      </div>
      <label className={`upload-zone ${preview ? "has-preview" : ""}`} htmlFor="image">
        <ImagePlus size={28} />
        <strong>{file ? "已选择图片" : "选择图片创建任务"}</strong>
        <span>{file ? file.name : "点击选择 JPG、PNG 或 WebP，建议优先使用产品主体清晰的素材"}</span>
        <input
          id="image"
          className="file-input"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(event) => selectFile(event.target.files?.[0] ?? null)}
        />
      </label>
      {preview ? (
        <div className="preview-box">
          {/* Local object URL is safe for a plain preview; Next image optimization is not needed. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview.url} alt="上传原图预览" />
          <div>
            <strong>{preview.name}</strong>
            <span>{formatFileSize(preview.size)}</span>
          </div>
        </div>
      ) : null}
      <div className="option-panel">
        <div className="option-heading">
          <SlidersHorizontal size={16} />
          <span>生成参数</span>
        </div>
        <div className="field">
          <label>倍率</label>
          <div className="segments">
            {["2", "4"].map((value) => (
              <button key={value} className={`segment ${scale === value ? "active" : ""}`} onClick={() => setScale(value)}>
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
              <button key={value} className={`segment ${mode === value ? "active" : ""}`} onClick={() => setMode(value)}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="field">
          <label htmlFor="scene">场景</label>
          <select id="scene" value={scene} onChange={(event) => setScene(event.target.value)}>
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
      </div>
      <button className="primary" disabled={!file || loading || candidates.length === 0} onClick={submit}>
        <Upload size={16} /> {loading ? "创建中" : "创建任务"}
      </button>
    </section>
  );
}
