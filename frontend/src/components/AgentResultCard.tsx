import {
  CodeAuditorResult,
  FinalJudgeResult,
  ProductAnalystResult,
} from "../api";

type Props = {
  title: string;
  result: CodeAuditorResult | ProductAnalystResult | FinalJudgeResult;
  type: "code" | "product" | "final";
};

export default function AgentResultCard({ title, result, type }: Props) {
  return (
    <article className="agent-card">
      <div className="agent-card-header">
        <h3>{title}</h3>
        <ScoreBadge result={result} type={type} />
      </div>

      {type === "product" && (
        <div className="detail-grid">
          <DetailItem
            label="README 清晰度"
            value={(result as ProductAnalystResult).readme_clarity}
          />
          <DetailItem
            label="开源活跃度"
            value={(result as ProductAnalystResult).open_source_activity}
          />
        </div>
      )}

      {type === "final" ? (
        <FinalJudgeContent result={result as FinalJudgeResult} />
      ) : (
        <AgentLists result={result as CodeAuditorResult | ProductAnalystResult} />
      )}
    </article>
  );
}

function ScoreBadge({
  result,
  type,
}: {
  result: CodeAuditorResult | ProductAnalystResult | FinalJudgeResult;
  type: Props["type"];
}) {
  const score =
    type === "final"
      ? (result as FinalJudgeResult).final_score
      : (result as CodeAuditorResult | ProductAnalystResult).score;

  return (
    <div className="score-badge">
      <span>{score}</span>
      <small>{type === "final" ? (result as FinalJudgeResult).level : "分"}</small>
    </div>
  );
}

function AgentLists({ result }: { result: CodeAuditorResult | ProductAnalystResult }) {
  return (
    <div className="list-columns">
      <TextList title="优势" items={result.strengths} />
      <TextList title="风险" items={result.risks} />
      <TextList title="建议" items={result.suggestions} />
    </div>
  );
}

function FinalJudgeContent({ result }: { result: FinalJudgeResult }) {
  return (
    <>
      <p className="summary">{result.summary}</p>
      <div className="dimension-row">
        <DetailItem label="代码质量" value={String(result.dimension_scores.code_quality)} />
        <DetailItem label="产品价值" value={String(result.dimension_scores.product_value)} />
        <DetailItem label="活跃度" value={String(result.dimension_scores.activity)} />
      </div>
      <div className="list-columns two">
        <TextList title="主要问题" items={result.top_issues} />
        <TextList title="优先建议" items={result.top_suggestions} />
      </div>
    </>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-item">
      <span>{label}</span>
      <strong>{value || "未提供"}</strong>
    </div>
  );
}

function TextList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="text-list">
      <h4>{title}</h4>
      {items.length > 0 ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>暂无</p>
      )}
    </div>
  );
}
