import { useMemo, useState } from "react";
import { submitFeedback, type JobRead } from "../lib/api";
import {
  buildEvaluationFeedbackComment,
  calculateEvaluationRating,
  type EvaluationScoreKey,
  type EvaluationScores
} from "../lib/evaluation";
import { resultTypeLabel, riskLabel } from "../lib/presentation";
import { ISSUE_TAGS } from "./FeedbackPanel";

type Props = {
  job: JobRead | null;
  onSubmitted: () => void;
};

type ScoreItem = {
  key: EvaluationScoreKey;
  label: string;
  hint: string;
};

const SCORE_ITEMS: ScoreItem[] = [
  { key: "clarity", label: "清晰度", hint: "边缘、纹理、压缩痕迹是否改善" },
  { key: "structure", label: "结构一致性", hint: "车身、轮胎、把手、灯组是否变形" },
  { key: "logoText", label: "Logo/文字", hint: "Logo、型号、仪表盘文字是否可信" },
  { key: "material", label: "材质真实感", hint: "金属、塑料、橡胶、漆面是否自然" },
  { key: "color", label: "颜色一致性", hint: "品牌色、阴影、曝光是否偏移" },
  { key: "usability", label: "可用性", hint: "是否能进入初稿或评审流程" }
];

const DEFAULT_SCORES: EvaluationScores = {
  clarity: 4,
  structure: 4,
  logoText: 3,
  material: 4,
  color: 4,
  usability: 4
};

export function EvaluationReportPanel({ job, onSubmitted }: Props) {
  const [selectedResultId, setSelectedResultId] = useState("");
  const [scores, setScores] = useState<EvaluationScores>(DEFAULT_SCORES);
  const [usable, setUsable] = useState(true);
  const [issues, setIssues] = useState<string[]>(["good"]);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedJobId, setSavedJobId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const selectedResult = useMemo(() => {
    if (!job?.results.length) {
      return null;
    }
    return job.results.find((result) => result.id === selectedResultId) ?? job.results[0];
  }, [job, selectedResultId]);

  const rating = calculateEvaluationRating(scores);

  function updateScore(key: EvaluationScoreKey, value: string) {
    setScores((current) => ({
      ...current,
      [key]: Number(value)
    }));
  }

  function toggleIssue(tag: string) {
    setIssues((current) => (current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag]));
  }

  async function submit() {
    if (!job || !selectedResult) {
      return;
    }
    setSaving(true);
    setError("");
    try {
      await submitFeedback(job.job_id, {
        selected_result_id: selectedResult.id,
        rating,
        usable,
        issues,
        comment: buildEvaluationFeedbackComment(scores, notes)
      });
      setSavedJobId(job.job_id);
      onSubmitted();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "评估保存失败，请确认后端服务是否已启动。");
    } finally {
      setSaving(false);
    }
  }

  if (!job) {
    return (
      <section>
        <h2 className="section-title">评估打分</h2>
        <p className="subtle">请先上传图片或从最近任务中选择一个已完成任务，再提交评估记录。</p>
      </section>
    );
  }

  if (job.results.length === 0) {
    return (
      <section>
        <h2 className="section-title">评估打分</h2>
        <p className="subtle">当前任务还没有候选结果。请先处理任务，生成结果后再按六维指标评估。</p>
      </section>
    );
  }

  return (
    <section>
      <div className="evaluation-heading">
        <div>
          <h2 className="section-title">评估打分</h2>
          <p className="subtle">评分会保存为结构化 feedback，用于后续评测报告和训练数据复盘。</p>
        </div>
        <div className="evaluation-rating">
          <span>综合分</span>
          <strong>{rating}/5</strong>
        </div>
      </div>

      <div className="review-target">
        <label htmlFor="evaluation-result">评估结果</label>
        <select
          id="evaluation-result"
          value={selectedResult?.id ?? ""}
          onChange={(event) => setSelectedResultId(event.target.value)}
        >
          {job.results.map((result) => (
            <option value={result.id} key={result.id}>
              {resultTypeLabel(result.type)} · {riskLabel(result.risk_level)} · {result.model_name}
            </option>
          ))}
        </select>
      </div>

      <div className="score-grid">
        {SCORE_ITEMS.map((item) => (
          <div className="score-row" key={item.key}>
            <div>
              <label htmlFor={`score-${item.key}`}>{item.label}</label>
              <span>{item.hint}</span>
            </div>
            <select
              id={`score-${item.key}`}
              value={scores[item.key]}
              onChange={(event) => updateScore(item.key, event.target.value)}
            >
              {[1, 2, 3, 4, 5].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      <div className="field compact-field">
        <label>
          <input type="checkbox" checked={usable} onChange={(event) => setUsable(event.target.checked)} /> 可进入初稿或评审流程
        </label>
      </div>

      <div className="field">
        <label>问题标签</label>
        <div className="feedback-tags">
          {ISSUE_TAGS.map(([tag, label]) => (
            <label key={tag}>
              <input type="checkbox" checked={issues.includes(tag)} onChange={() => toggleIssue(tag)} /> {label}
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <label htmlFor="evaluation-notes">评审备注</label>
        <textarea
          id="evaluation-notes"
          rows={3}
          value={notes}
          placeholder="例如：车身边缘更清晰，但 Logo 需要人工回贴。"
          onChange={(event) => setNotes(event.target.value)}
        />
      </div>

      <button className="primary" disabled={saving || !selectedResult} onClick={submit}>
        {saving ? "保存中..." : "保存评估记录"}
      </button>
      {savedJobId === job.job_id ? <p className="success-text">评估记录已保存，可用于后续报告导出和样本复盘。</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}
