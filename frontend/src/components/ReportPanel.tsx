import { AnalyzeResponse } from "../api";
import AgentResultCard from "./AgentResultCard";

type Props = {
  report: AnalyzeResponse;
};

export default function ReportPanel({ report }: Props) {
  const repo = report.repo_context;
  const primaryLanguage = getPrimaryLanguage(repo.languages);

  return (
    <section className="report-panel" aria-label="体检报告">
      <div className="repo-summary">
        <div>
          <p className="eyebrow">Repository</p>
          <h2>
            {repo.owner}/{repo.repo}
          </h2>
          {repo.description && <p>{repo.description}</p>}
        </div>
        <div className="metrics">
          <Metric label="Stars" value={String(repo.stars)} />
          <Metric label="Forks" value={String(repo.forks)} />
          <Metric label="主要语言" value={primaryLanguage} />
        </div>
      </div>

      <div className="final-strip">
        <span>最终评分</span>
        <strong>{report.agents.final_judge.final_score}</strong>
        <span>等级 {report.agents.final_judge.level}</span>
      </div>

      <div className="agent-grid">
        <AgentResultCard
          title="代码审计 Agent"
          type="code"
          result={report.agents.code_auditor}
        />
        <AgentResultCard
          title="产品价值 Agent"
          type="product"
          result={report.agents.product_analyst}
        />
        <AgentResultCard
          title="最终裁判 Agent"
          type="final"
          result={report.agents.final_judge}
        />
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function getPrimaryLanguage(languages: Record<string, number>) {
  const [language] =
    Object.entries(languages).sort((left, right) => right[1] - left[1])[0] || [];

  return language || "未知";
}
