"use client";

import {
  ClipboardCheck,
  Download,
  FileText,
  History,
  Images,
  Layers3,
  Plus,
  RefreshCw,
  ShieldCheck,
  Table2,
  UploadCloud
} from "lucide-react";
import { useEffect, useState } from "react";
import { BatchUploadPanel } from "../components/BatchUploadPanel";
import { EvaluationReportPanel } from "../components/EvaluationReportPanel";
import { FeedbackPanel } from "../components/FeedbackPanel";
import { JobHistory } from "../components/JobHistory";
import { JobStatus } from "../components/JobStatus";
import { ResultCompare } from "../components/ResultCompare";
import { Uploader } from "../components/Uploader";
import {
  batchDownloadUrl,
  getJob,
  listJobs,
  processJob,
  reportDownloadUrl,
  riskSamplesDownloadUrl,
  type JobRead,
  type JobSummaryRead
} from "../lib/api";
import { statusLabel } from "../lib/presentation";

export type PreviewImage = {
  url: string;
  name: string;
  size: number;
};

type ViewName = "workspace" | "batch" | "history" | "evaluation";

const viewMeta: Record<ViewName, { title: string; subtitle: string }> = {
  workspace: {
    title: "上传工作台",
    subtitle: "上传单张产品或营销素材，选择倍率和模式后创建高清放大任务。"
  },
  history: {
    title: "最近任务",
    subtitle: "查看任务状态、恢复历史结果，并对需要复核的素材做二次处理。"
  },
  batch: {
    title: "批量处理",
    subtitle: "一次上传多张图片生成独立任务，适合内部评审前的小批量验证。"
  },
  evaluation: {
    title: "评测说明",
    subtitle: "围绕清晰度、真实感、产品一致性和人工复核风险沉淀评估记录。"
  }
};

const navItems = [
  { view: "workspace", label: "上传工作台", Icon: UploadCloud },
  { view: "history", label: "最近任务", Icon: History },
  { view: "batch", label: "批量处理", Icon: Images },
  { view: "evaluation", label: "评测说明", Icon: ClipboardCheck }
] satisfies Array<{ view: ViewName; label: string; Icon: typeof UploadCloud }>;

export default function Page() {
  const [job, setJob] = useState<JobRead | null>(null);
  const [message, setMessage] = useState("等待上传图片");
  const [preview, setPreview] = useState<PreviewImage | null>(null);
  const [history, setHistory] = useState<JobSummaryRead[]>([]);
  const [lastBatchId, setLastBatchId] = useState<string | null>(null);
  const [view, setView] = useState<ViewName>("workspace");
  const activeView = viewMeta[view];
  const reviewCount = history.filter((item) => item.risk_level !== "low").length;

  async function refreshJob(jobId: string) {
    const nextJob = await getJob(jobId);
    setJob(nextJob);
    setMessage(`任务状态：${statusLabel(nextJob.status)}`);
  }

  async function refreshHistory() {
    const list = await listJobs();
    setHistory(list.jobs);
  }

  async function selectHistoryJob(jobId: string) {
    window.localStorage.setItem("ninebot-upscale-last-job-id", jobId);
    await refreshJob(jobId);
    setPreview(null);
    setView("history");
  }

  async function processHistoryJob(jobId: string) {
    setMessage(`正在处理历史任务：${jobId}`);
    const processed = await processJob(jobId);
    setJob(processed);
    window.localStorage.setItem("ninebot-upscale-last-job-id", jobId);
    setPreview(null);
    await refreshHistory();
    setMessage(`任务状态：${statusLabel(processed.status)}`);
    setView("history");
  }

  async function processCurrentJob(jobId: string) {
    setMessage(`正在处理任务：${jobId}`);
    const processed = await processJob(jobId);
    setJob(processed);
    window.localStorage.setItem("ninebot-upscale-last-job-id", jobId);
    await refreshHistory();
    setMessage(`任务状态：${statusLabel(processed.status)}`);
  }

  function clearSelection() {
    window.localStorage.removeItem("ninebot-upscale-last-job-id");
    setJob(null);
    setPreview(null);
    setMessage("已清除当前选择，历史记录不会删除");
  }

  function startBlankTask() {
    window.localStorage.removeItem("ninebot-upscale-last-job-id");
    setJob(null);
    setPreview(null);
    setView("workspace");
    setMessage("已进入新任务，请选择图片");
  }

  useEffect(() => {
    const lastJobId = window.localStorage.getItem("ninebot-upscale-last-job-id");
    if (!lastJobId) {
      const historyTimer = window.setTimeout(() => {
        refreshHistory().catch(() => setMessage("历史任务加载失败，请确认后端服务是否启动"));
      }, 0);
      return () => window.clearTimeout(historyTimer);
    }
    const timer = window.setTimeout(() => {
      setLastBatchId(window.localStorage.getItem("ninebot-upscale-last-batch-id"));
      refreshHistory().catch(() => setMessage("历史任务加载失败，请确认后端服务是否启动"));
      refreshJob(lastJobId)
        .then(() => setMessage(`已恢复最近任务：${lastJobId}`))
        .catch(() => {
          window.localStorage.removeItem("ninebot-upscale-last-job-id");
          setMessage("最近任务恢复失败，请重新上传");
        });
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) {
      return;
    }
    const timer = window.setTimeout(() => {
      refreshJob(job.job_id).catch(() => setMessage("任务查询失败，请确认后端服务是否启动"));
      refreshHistory().catch(() => undefined);
    }, 4000);
    return () => window.clearTimeout(timer);
  }, [job]);

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-kicker">AI IMAGE UPSCALE</span>
          <h1 className="brand">九号高清放大 MVP</h1>
          <p className="subtle">
            面向内部产品图、营销图、电商详情页图的 2x/4x 高清放大工具。
          </p>
          <div className="sidebar-status">
            <span>本地推理</span>
            <span>2x / 4x</span>
            <span>人工复核</span>
          </div>
        </div>
        <div className="demo-note">
          <strong>审核边界</strong>
          <p>公开样本只证明工程链路。九号内部评审需要使用授权产品/营销素材，并对 Logo、型号、仪表盘和文字做人工审核。</p>
        </div>
        <div className="flow-guide" aria-label="演示流程">
          <span className="flow-caption">流程指示</span>
          <ol>
            <li>
              <span>1</span>
              上传图片
            </li>
            <li>
              <span>2</span>
              处理任务
            </li>
            <li>
              <span>3</span>
              对比结果
            </li>
            <li>
              <span>4</span>
              提交反馈
            </li>
          </ol>
        </div>
        <nav className="side-nav">
          {navItems.map(({ view: itemView, label, Icon }) => (
            <button
              key={itemView}
              type="button"
              className={view === itemView ? "active" : ""}
              onClick={() => {
                setView(itemView);
                if (itemView === "history") {
                  refreshHistory().catch(() => setMessage("历史任务加载失败，请确认后端服务是否启动"));
                }
              }}
            >
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </aside>
      <section className="main">
        <div className="workspace-hero">
          <div className="workspace-copy">
            <span className="eyebrow">Ninebot Internal AI Tool</span>
            <h2>{activeView.title}</h2>
            <p>{activeView.subtitle}</p>
            <div className="message-pill">
              <ShieldCheck size={15} />
              <span>{message}</span>
            </div>
          </div>
          <div className="hero-actions">
            <div className="action-cluster">
              <span>任务操作</span>
              {job ? (
                <button className="secondary" onClick={() => refreshJob(job.job_id)}>
                  <RefreshCw size={15} />
                  查询状态
                </button>
              ) : null}
              <button className="secondary" onClick={startBlankTask}>
                <Plus size={15} />
                新任务
              </button>
            </div>
            {lastBatchId ? (
              <div className="action-cluster">
                <span>批量导出</span>
                <a className="secondary toolbar-link" href={batchDownloadUrl(lastBatchId)}>
                  <Download size={15} />
                  下载批量
                </a>
                <a className="secondary toolbar-link" href={reportDownloadUrl(lastBatchId)}>
                  <FileText size={15} />
                  评测报告
                </a>
                <a className="secondary toolbar-link" href={reportDownloadUrl(lastBatchId, "csv")}>
                  <Table2 size={15} />
                  CSV
                </a>
                <a className="secondary toolbar-link" href={riskSamplesDownloadUrl(lastBatchId)}>
                  <Layers3 size={15} />
                  风险样本
                </a>
              </div>
            ) : null}
          </div>
        </div>
        <div className="metric-strip">
          <div className="metric-card">
            <span>当前任务</span>
            <strong>{job ? statusLabel(job.status) : "未选择"}</strong>
          </div>
          <div className="metric-card">
            <span>最近任务</span>
            <strong>{history.length} 条</strong>
          </div>
          <div className="metric-card">
            <span>需复核</span>
            <strong>{reviewCount} 条</strong>
          </div>
        </div>
        {view === "workspace" ? (
          <div className="grid">
            <div className="panel">
              <Uploader
                preview={preview}
                onPreviewChanged={setPreview}
                onError={setMessage}
                onCreated={(created) => {
                  window.localStorage.setItem("ninebot-upscale-last-job-id", created.job_id);
                  setMessage(`任务已创建：${created.job_id}`);
                  refreshJob(created.job_id)
                    .then(() => refreshHistory())
                    .catch(() => setMessage("任务查询失败"));
                }}
              />
              <JobStatus
                job={job}
                onProcess={(jobId) => processCurrentJob(jobId).catch(() => setMessage("历史任务处理失败，请确认后端 Real-ESRGAN 配置"))}
              />
            </div>
            <div className="panel">
              <ResultCompare job={job} preview={preview} />
              <FeedbackPanel job={job} onSubmitted={() => setMessage("反馈已提交")} />
            </div>
          </div>
        ) : null}
        {view === "history" ? (
          <div className="history-layout">
            <div className="panel">
              <JobHistory
                jobs={history}
                activeJobId={job?.job_id}
                onSelect={(jobId) => selectHistoryJob(jobId).catch(() => setMessage("历史任务恢复失败"))}
                onProcess={(jobId) => processHistoryJob(jobId).catch(() => setMessage("历史任务处理失败，请确认后端 Real-ESRGAN 配置"))}
                onClearSelection={clearSelection}
              />
            </div>
            <div className="panel">
              <JobStatus
                job={job}
                onProcess={(jobId) => processCurrentJob(jobId).catch(() => setMessage("历史任务处理失败，请确认后端 Real-ESRGAN 配置"))}
              />
              <ResultCompare job={job} preview={preview} />
              <FeedbackPanel job={job} onSubmitted={() => setMessage("反馈已提交")} />
            </div>
          </div>
        ) : null}
        {view === "batch" ? (
          <div className="batch-layout">
            <div className="panel">
              <BatchUploadPanel
                onError={setMessage}
                onCreated={(batch) => {
                  const firstJobId = batch.job_ids[0];
                  if (firstJobId) {
                    window.localStorage.setItem("ninebot-upscale-last-job-id", firstJobId);
                  }
                  window.localStorage.setItem("ninebot-upscale-last-batch-id", batch.batch_id);
                  setLastBatchId(batch.batch_id);
                  setPreview(null);
                  setMessage(`批量任务已创建：${batch.created_count} 张`);
                  refreshHistory()
                    .then(() => {
                      if (firstJobId) {
                        return refreshJob(firstJobId);
                      }
                      return undefined;
                    })
                    .then(() => setView("history"))
                    .catch(() => setMessage("批量任务已创建，但历史任务加载失败"));
                }}
              />
            </div>
            <div className="panel">
              <h2 className="section-title">批量处理说明</h2>
              <div className="info-list">
                <div>
                  <strong>独立任务</strong>
                  <span>每张图片都会成为独立任务，后续可以单独查看状态、结果和风险提示。</span>
                </div>
                <div>
                  <strong>建议节奏</strong>
                  <span>公司演示前先跑 2-10 张公开样本确认链路，再换成已授权素材。</span>
                </div>
                <div>
                  <strong>人工复核</strong>
                  <span>带 Logo、型号、仪表盘或文字的图片仍要人工复核，不自动作为最终商用图。</span>
                </div>
              </div>
            </div>
          </div>
        ) : null}
        {view === "evaluation" ? (
          <div className="evaluation-layout">
            <div className="panel">
              <h2 className="section-title">评测说明</h2>
              <p className="subtle">
                当前阶段重点评估清晰度提升、产品结构一致性、Logo/文字正确性、材质真实感、颜色一致性和是否需要人工修图。
              </p>
              <div className="info-list">
                <div>
                  <strong>小样本冒烟</strong>
                  <span>先用 10 张授权素材判断链路和效果是否稳定，每张图至少保存一条评估记录。</span>
                </div>
                <div>
                  <strong>正式评测</strong>
                  <span>小样本通过后再扩展到 100 张评测集，并导出人工评分报告。</span>
                </div>
              </div>
            </div>
            <div className="panel">
              <EvaluationReportPanel job={job} onSubmitted={() => setMessage("评估记录已提交")} />
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
