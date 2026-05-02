import { CircleDashed, Play, ShieldAlert } from "lucide-react";
import type { JobRead } from "../lib/api";
import { modeLabel, statusLabel, warningLabel } from "../lib/presentation";

type Props = {
  job: JobRead | null;
  onProcess?: (jobId: string) => void;
};

export function JobStatus({ job, onProcess }: Props) {
  if (!job) {
    return (
      <section className="status-panel">
        <div className="panel-heading">
          <div>
            <h2 className="section-title">任务状态</h2>
            <p className="subtle">暂无当前任务。可以先上传一张图片创建任务，或从最近任务中恢复历史记录。</p>
          </div>
          <span className="panel-icon">
            <CircleDashed size={18} />
          </span>
        </div>
        <div className="empty-state compact-empty">
          <strong>等待任务进入处理队列</strong>
          <span>创建任务后会显示倍率、模式、风险提示和手动处理入口。</span>
        </div>
      </section>
    );
  }

  return (
    <section className="status-panel">
      <div className="panel-heading">
        <div>
          <h2 className="section-title">任务状态</h2>
          <p className="subtle">跟踪当前图片从创建、处理到完成的状态。</p>
        </div>
        <span className={`status-dot status-${job.status}`}>{statusLabel(job.status)}</span>
      </div>
      <div className="status-list">
        <div className="status-item">
          <span>任务 ID</span>
          <code>{job.job_id}</code>
        </div>
        <div className="status-item">
          <span>状态</span>
          <span className={`badge status-${job.status}`}>{statusLabel(job.status)}</span>
        </div>
        <div className="status-item">
          <span>倍率</span>
          <span>{job.scale}x</span>
        </div>
        <div className="status-item">
          <span>模式</span>
          <span>{modeLabel(job.mode)}</span>
        </div>
      </div>
      {job.status === "queued" ? (
        <div className="pending-panel">
          <strong>任务已创建，等待推理服务处理</strong>
          <p>如果本地没有启动 worker 或 inline 处理，可以点击处理任务手动触发一次生成。</p>
          {onProcess ? (
            <button type="button" className="secondary small-button" onClick={() => onProcess(job.job_id)}>
              <Play size={14} />
              处理任务
            </button>
          ) : null}
        </div>
      ) : null}
      {job.warnings.length > 0 ? (
        <div className="risk-panel">
          <strong>
            <ShieldAlert size={15} />
            风险提示
          </strong>
          <ul>
            {job.warnings.map((warning) => (
              <li key={warning}>{warningLabel(warning)}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
