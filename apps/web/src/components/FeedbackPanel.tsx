import { useState } from "react";
import { submitFeedback, type JobRead } from "../lib/api";

export const ISSUE_TAGS = [
  ["good", "效果好"],
  ["text_blur", "文字模糊"],
  ["logo_error", "Logo/型号错误"],
  ["structure_changed", "结构变化"],
  ["oversharpen", "过锐化"],
  ["fake_texture", "虚假纹理"],
  ["color_shift", "颜色偏移"],
  ["too_slow", "处理较慢"],
  ["other", "其他"]
] as const;

export function FeedbackPanel({ job, onSubmitted }: { job: JobRead | null; onSubmitted: () => void }) {
  const [selectedResultId, setSelectedResultId] = useState("");
  const [rating, setRating] = useState("4");
  const [usable, setUsable] = useState(true);
  const [issues, setIssues] = useState<string[]>(["good"]);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function submit() {
    if (!job || !selectedResultId) {
      return;
    }
    await submitFeedback(job.job_id, {
      selected_result_id: selectedResultId,
      rating: Number(rating),
      usable,
      issues,
      comment
    });
    setSubmitted(true);
    onSubmitted();
  }

  function toggleIssue(tag: string) {
    setIssues((current) => (current.includes(tag) ? current.filter((item) => item !== tag) : [...current, tag]));
  }

  return (
    <section style={{ marginTop: 18 }}>
      <h2 className="section-title">反馈</h2>
      {!job || job.results.length === 0 ? <p className="subtle">有候选结果后可以提交反馈。</p> : null}
      {job && job.results.length > 0 ? (
        <>
          <div className="field">
            <label htmlFor="result">最佳结果</label>
            <select id="result" value={selectedResultId} onChange={(event) => setSelectedResultId(event.target.value)}>
              <option value="">请选择</option>
              {job.results.map((result) => (
                <option value={result.id} key={result.id}>{result.type}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="rating">评分</label>
            <select id="rating" value={rating} onChange={(event) => setRating(event.target.value)}>
              {[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </div>
          <div className="field">
            <label>
              <input type="checkbox" checked={usable} onChange={(event) => setUsable(event.target.checked)} /> 可用于初稿
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
            <label htmlFor="comment">备注</label>
            <textarea id="comment" rows={3} value={comment} onChange={(event) => setComment(event.target.value)} />
          </div>
          <button className="primary" disabled={!selectedResultId} onClick={submit}>提交反馈</button>
          {submitted ? <p className="success-text">反馈已保存，可用于后续评测和模型优化。</p> : null}
        </>
      ) : null}
    </section>
  );
}
