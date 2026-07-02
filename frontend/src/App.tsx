import { Activity, Loader2 } from "lucide-react";
import { FormEvent, useRef, useState } from "react";

import { AnalyzeResponse, StreamEvent, analyzeRepo, analyzeRepoStream } from "./api";
import ReportPanel from "./components/ReportPanel";

export default function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [report, setReport] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [progressEvents, setProgressEvents] = useState<StreamEvent[]>([]);
  const streamRef = useRef<{ close: () => void } | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedUrl = repoUrl.trim();
    if (!normalizedUrl) {
      setError("请输入 GitHub 仓库 URL");
      setReport(null);
      return;
    }

    setLoading(true);
    setError("");
    setReport(null);
    setProgressEvents([]);
    streamRef.current?.close();

    if ("EventSource" in window) {
      streamRef.current = analyzeRepoStream(normalizedUrl, {
        onProgress: (event) => {
          setProgressEvents((current) => [...current, event]);
        },
        onDone: (result) => {
          setReport(result);
          setLoading(false);
          streamRef.current = null;
        },
        onError: (message) => {
          setError(message);
          setLoading(false);
          streamRef.current = null;
        },
      });
      return;
    }

    try {
      const result = await analyzeRepo(normalizedUrl);
      setReport(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "体检请求失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="app-header">
          <div>
            <p className="eyebrow">GitHub Repo Health</p>
            <h1>GitHub 仓库体检工具</h1>
          </div>
          <p className="header-copy">
            输入公开仓库地址，查看代码工程质量、产品价值和最终建议。
          </p>
        </header>

        <form className="analyze-form" onSubmit={handleSubmit}>
          <label htmlFor="repo-url">GitHub 仓库 URL</label>
          <div className="input-row">
            <input
              id="repo-url"
              value={repoUrl}
              onChange={(event) => setRepoUrl(event.target.value)}
              placeholder="https://github.com/langchain-ai/langgraph"
              disabled={loading}
            />
            <button type="submit" disabled={loading}>
              {loading ? (
                <Loader2 aria-hidden="true" className="spin" size={18} />
              ) : (
                <Activity aria-hidden="true" size={18} />
              )}
              <span>{loading ? "正在体检..." : "开始体检"}</span>
            </button>
          </div>
        </form>

        {loading && <div className="status-line">正在体检...</div>}
        {error && <div className="error-box">{error}</div>}
        {progressEvents.length > 0 && <ProgressList events={progressEvents} />}

        {report ? (
          <ReportPanel report={report} />
        ) : (
          !loading &&
          !error && (
            <section className="empty-state">
              <h2>等待输入仓库地址</h2>
              <p>报告会展示仓库基础信息、三个 Agent 的分析结果和最终评分。</p>
            </section>
          )
        )}
      </section>
    </main>
  );
}

function ProgressList({ events }: { events: StreamEvent[] }) {
  return (
    <section className="progress-panel" aria-label="阶段进度">
      <h2>阶段进度</h2>
      <ol>
        {events.map((event, index) => (
          <li key={`${event.stage}-${index}`}>
            <span>{stageLabel(event.stage)}</span>
            <strong>{event.message}</strong>
          </li>
        ))}
      </ol>
    </section>
  );
}

function stageLabel(stage: StreamEvent["stage"]) {
  const labels: Record<StreamEvent["stage"], string> = {
    parsing_url: "解析",
    fetching_github: "GitHub",
    code_audit: "Agent A",
    product_analysis: "Agent B",
    final_judge: "Agent C",
    done: "完成",
    error: "失败",
  };

  return labels[stage];
}
