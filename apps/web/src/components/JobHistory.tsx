import { useMemo, useState } from "react";
import { Filter, History, XCircle } from "lucide-react";
import { assetUrl } from "../lib/api";
import type { JobSummaryRead } from "../lib/api";
import { modeLabel, riskLabel, statusLabel } from "../lib/presentation";

type Props = {
  jobs: JobSummaryRead[];
  activeJobId?: string;
  onSelect: (jobId: string) => void;
  onProcess: (jobId: string) => void;
  onClearSelection: () => void;
};

export function JobHistory({ jobs, activeJobId, onSelect, onProcess, onClearSelection }: Props) {
  const [filter, setFilter] = useState<"all" | "running" | "completed" | "failed" | "review">("all");
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      if (filter === "all") {
        return true;
      }
      if (filter === "running") {
        return job.status === "queued" || job.status === "running";
      }
      if (filter === "review") {
        return job.risk_level !== "low";
      }
      return job.status === filter;
    });
  }, [filter, jobs]);
  function processButtonLabel(status: JobSummaryRead["status"]) {
    if (status === "failed") {
      return "重新处理";
    }
    if (status === "running") {
      return "处理中";
    }
    return "处理任务";
  }

  return (
    <section className="history-section">
      <div className="history-title-row">
        <div>
          <h2 className="section-title">最近任务</h2>
          <p className="subtle">按状态筛选任务，点击卡片在右侧恢复结果详情。</p>
        </div>
        <button type="button" className="link-button icon-link" onClick={onClearSelection}>
          <XCircle size={14} />
          清除选择
        </button>
      </div>
      {jobs.length === 0 ? (
        <div className="empty-state compact-empty">
          <History size={24} />
          <strong>暂无历史任务</strong>
          <span>可以先上传一张图片创建任务，生成后会在这里沉淀记录。</span>
        </div>
      ) : null}
      {jobs.length > 0 ? (
        <div className="history-filters">
          <span>
            <Filter size={13} />
            筛选
          </span>
          {[
            ["all", "全部"],
            ["running", "处理中"],
            ["completed", "完成"],
            ["failed", "失败"],
            ["review", "需复核"]
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={filter === value ? "active" : ""}
              onClick={() => setFilter(value as typeof filter)}
            >
              {label}
            </button>
          ))}
        </div>
      ) : null}
      <div className="history-list">
        {filteredJobs.map((job) => (
          <article
            key={job.job_id}
            className={`history-item ${job.job_id === activeJobId ? "active" : ""}`}
          >
            <button type="button" className="history-open" onClick={() => onSelect(job.job_id)}>
              {job.thumbnail_url ? (
                <span className="history-thumb">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={assetUrl(job.thumbnail_url)} alt="任务缩略图" />
                </span>
              ) : null}
              <span className="history-main">
                <strong>{job.scene}</strong>
                <code>{job.job_id}</code>
              </span>
              <span className="history-meta">
                <span>{job.scale}x / {modeLabel(job.mode)}</span>
                <span>{statusLabel(job.status)} / {job.result_count} 个结果</span>
                <span>{new Date(job.created_at).toLocaleString()}</span>
                <span className={`risk-badge risk-${job.risk_level}`}>{riskLabel(job.risk_level)}</span>
              </span>
            </button>
            <div className="history-actions">
              {job.status === "completed" && job.result_url ? (
                <a className="secondary small-link-button" href={assetUrl(job.result_url)} download>
                  下载结果
                </a>
              ) : null}
              {job.status !== "completed" ? (
                <button type="button" className="secondary small-button" disabled={job.status === "running"} onClick={() => onProcess(job.job_id)}>
                  {processButtonLabel(job.status)}
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
      {jobs.length > 0 && filteredJobs.length === 0 ? <p className="subtle">当前筛选下暂无任务。</p> : null}
    </section>
  );
}
