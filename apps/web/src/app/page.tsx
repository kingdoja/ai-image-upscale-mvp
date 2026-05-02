"use client";

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

export default function Page() {
  const [job, setJob] = useState<JobRead | null>(null);
  const [message, setMessage] = useState("等待上传图片");
  const [preview, setPreview] = useState<PreviewImage | null>(null);
  const [history, setHistory] = useState<JobSummaryRead[]>([]);
  const [lastBatchId, setLastBatchId] = useState<string | null>(null);
  const [view, setView] = useState<"workspace" | "batch" | "history" | "samples" | "evaluation">("workspace");

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
            <span>MVP v0.1</span>
            <span>本地推理</span>
            <span>内部演示</span>
          </div>
        </div>
        <div className="demo-note">
          <strong>演示边界</strong>
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
          <button type="button" className={view === "workspace" ? "active" : ""} onClick={() => setView("workspace")}>
            上传工作台
          </button>
          <button
            type="button"
            className={view === "history" ? "active" : ""}
            onClick={() => {
              setView("history");
              refreshHistory().catch(() => setMessage("历史任务加载失败，请确认后端服务是否启动"));
            }}
          >
            最近任务
          </button>
          <button type="button" className={view === "batch" ? "active" : ""} onClick={() => setView("batch")}>
            批量处理
          </button>
          <button type="button" className={view === "samples" ? "active" : ""} onClick={() => setView("samples")}>
            演示准备
          </button>
          <button type="button" className={view === "evaluation" ? "active" : ""} onClick={() => setView("evaluation")}>
            评测说明
          </button>
        </nav>
      </aside>
      <section className="main">
        <div className="toolbar">
          <div>
            <div className="section-title">任务工作台</div>
            <div className="subtle">{message}</div>
          </div>
          <div className="toolbar-actions">
            {job ? <button className="secondary" onClick={() => refreshJob(job.job_id)}>查询状态</button> : null}
            {lastBatchId ? (
              <a className="secondary toolbar-link" href={batchDownloadUrl(lastBatchId)}>
                下载最近批量
              </a>
            ) : null}
            {lastBatchId ? (
              <a className="secondary toolbar-link" href={reportDownloadUrl(lastBatchId)}>
                导出评测报告
              </a>
            ) : null}
            {lastBatchId ? (
              <a className="secondary toolbar-link" href={reportDownloadUrl(lastBatchId, "csv")}>
                导出CSV
              </a>
            ) : null}
            {lastBatchId ? (
              <a className="secondary toolbar-link" href={riskSamplesDownloadUrl(lastBatchId)}>
                导出风险样本
              </a>
            ) : null}
            <button className="secondary" onClick={startBlankTask}>新任务</button>
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
        {view === "samples" ? (
          <div className="panel">
            <h2 className="section-title">演示准备</h2>
            <p className="subtle">
              当前 MVP 不内置公司样本图，也不会自动读取本地目录。这里用于准备演示素材和跳转到实际操作入口。
            </p>
            <div className="demo-actions">
              <button className="secondary" type="button" onClick={() => setView("workspace")}>
                上传单张图
              </button>
              <button className="secondary" type="button" onClick={() => setView("batch")}>
                批量处理
              </button>
              <button
                className="secondary"
                type="button"
                onClick={() => {
                  setView("history");
                  refreshHistory().catch(() => setMessage("历史任务加载失败，请确认后端服务是否启动"));
                }}
              >
                查看最近任务
              </button>
              <button className="secondary" type="button" onClick={() => setView("evaluation")}>
                去评分评测
              </button>
            </div>
            <div className="info-list">
              <div>
                <strong>样本准备清单</strong>
                <span>建议准备产品主体图、局部材质图、带 Logo/型号/仪表盘文字的图片，以及营销图或电商详情页图。</span>
              </div>
              <div>
                <strong>本地公开样本</strong>
                <span>`test-tmp/public-smoke-samples` 只用于工程链路验证，不代表九号内部素材的正式效果。</span>
              </div>
              <div>
                <strong>公司演示素材</strong>
                <span>给九号内部评审时，请手动上传已授权的产品图、营销图或电商详情页素材，并对 Logo、型号、文字和仪表盘区域做人工复核。</span>
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
