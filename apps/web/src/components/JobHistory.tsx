import type { JobSummaryRead } from "../lib/api";
import { modeLabel, statusLabel } from "../lib/presentation";

type Props = {
  jobs: JobSummaryRead[];
  activeJobId?: string;
  onSelect: (jobId: string) => void;
  onProcess: (jobId: string) => void;
  onClearSelection: () => void;
};

export function JobHistory({ jobs, activeJobId, onSelect, onProcess, onClearSelection }: Props) {
  return (
    <section className="history-section">
      <div className="history-title-row">
        <h2 className="section-title">最近任务</h2>
        <button type="button" className="link-button" onClick={onClearSelection}>清除选择</button>
      </div>
      {jobs.length === 0 ? <p className="subtle">暂无历史任务，可以先上传一张图片创建任务。</p> : null}
      <div className="history-list">
        {jobs.map((job) => (
          <article
            key={job.job_id}
            className={`history-item ${job.job_id === activeJobId ? "active" : ""}`}
          >
            <button type="button" className="history-open" onClick={() => onSelect(job.job_id)}>
              <span className="history-main">
                <strong>{job.scene}</strong>
                <code>{job.job_id}</code>
              </span>
              <span className="history-meta">
                <span>{job.scale}x / {modeLabel(job.mode)}</span>
                <span>{statusLabel(job.status)} / {job.result_count} 个结果</span>
              </span>
            </button>
            {job.status !== "completed" ? (
              <button type="button" className="secondary small-button" onClick={() => onProcess(job.job_id)}>
                处理任务
              </button>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
