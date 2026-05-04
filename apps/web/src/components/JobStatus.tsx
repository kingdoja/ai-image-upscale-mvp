import { CircleDashed, Play, ShieldAlert } from "lucide-react";
import type { JobRead } from "../lib/api";
import { modeLabel, resultTypeLabel, semanticLabel, statusLabel, warningLabel } from "../lib/presentation";

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
      <div className="semantic-panel">
        <div>
          <strong>智能总控</strong>
          <span>{job.understanding.review_required ? "已标记复核区域" : "低风险保真处理"}</span>
        </div>
        <div className="semantic-grid">
          <section>
            <span>图像理解</span>
            <p>
              {[...job.understanding.degradation_types, ...job.understanding.subject_hints]
                .map(semanticLabel)
                .join(" / ")}
            </p>
          </section>
          <section>
            <span>修复计划</span>
            <p>
              {job.upscale_plan.candidate_types.map(resultTypeLabel).join(" / ")} ·{" "}
              {semanticLabel(job.upscale_plan.enhancement_policy)}
            </p>
          </section>
          <section>
            <span>路由原因</span>
            <p>{job.routing_decision.reasons.map(semanticLabel).join(" / ")}</p>
          </section>
          <section>
            <span>数据治理</span>
            <p>
              {semanticLabel(job.data_governance.usage_scope)} · {semanticLabel(job.data_governance.training_state)}
            </p>
          </section>
        </div>
        {job.upscale_plan.protected_regions.length > 0 ? (
          <p className="semantic-note">
            保护区域：
            {job.upscale_plan.protected_region_details
              .map((region) => {
                const bbox = region.bbox ? ` / ${region.bbox.join(",")}` : "";
                return `${semanticLabel(region.type)} / ${semanticLabel(region.policy)} / ${semanticLabel(region.source)}${bbox}`;
              })
              .join("；")}
          </p>
        ) : null}
        {job.routing_decision.skipped_candidate_types.length > 0 ? (
          <p className="semantic-note">
            未生成候选：
            {job.routing_decision.skipped_candidate_types
              .map((type) => `${resultTypeLabel(type)}（${semanticLabel(job.routing_decision.skip_reasons[type] ?? "")}）`)
              .join("；")}
          </p>
        ) : null}
        <p className="semantic-note">
          版本：{job.understanding.controller_version} · {job.routing_decision.policy_version}
        </p>
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
