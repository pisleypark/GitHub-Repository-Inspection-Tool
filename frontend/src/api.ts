export type RepoContext = {
  owner: string;
  repo: string;
  repo_url?: string;
  stars: number;
  forks: number;
  description?: string | null;
  default_branch?: string;
  updated_at?: string;
  languages: Record<string, number>;
  readme?: string;
  file_paths?: string[];
};

export type CodeAuditorResult = {
  score: number;
  strengths: string[];
  risks: string[];
  suggestions: string[];
};

export type ProductAnalystResult = {
  score: number;
  readme_clarity: string;
  open_source_activity: string;
  strengths: string[];
  risks: string[];
  suggestions: string[];
};

export type FinalJudgeResult = {
  final_score: number;
  level: "A" | "B" | "C" | "D" | string;
  summary: string;
  dimension_scores: {
    code_quality: number;
    product_value: number;
    activity: number;
  };
  top_issues: string[];
  top_suggestions: string[];
};

export type AnalyzeResponse = {
  repo_context: RepoContext;
  agents: {
    code_auditor: CodeAuditorResult;
    product_analyst: ProductAnalystResult;
    final_judge: FinalJudgeResult;
  };
};

export type StreamStage =
  | "parsing_url"
  | "fetching_github"
  | "code_audit"
  | "product_analysis"
  | "final_judge"
  | "done"
  | "error";

export type StreamEvent = {
  stage: StreamStage;
  message: string;
  data: AnalyzeResponse | null;
};

export type StreamHandlers = {
  onProgress: (event: StreamEvent) => void;
  onDone: (report: AnalyzeResponse) => void;
  onError: (message: string) => void;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export async function analyzeRepo(repoUrl: string): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      body && typeof body.detail === "string"
        ? body.detail
        : "体检请求失败，请稍后重试";
    throw new Error(message);
  }

  return body as AnalyzeResponse;
}

export function analyzeRepoStream(
  repoUrl: string,
  handlers: StreamHandlers,
): { close: () => void } {
  const url = `${API_BASE_URL}/analyze/stream?repo_url=${encodeURIComponent(repoUrl)}`;
  const source = new EventSource(url);
  let closedByClient = false;

  const close = () => {
    closedByClient = true;
    source.close();
  };

  source.onmessage = (event) => {
    let payload: StreamEvent;
    try {
      payload = JSON.parse(event.data) as StreamEvent;
    } catch {
      handlers.onError("无法解析流式分析结果");
      close();
      return;
    }

    if (payload.stage === "done") {
      close();
      handlers.onDone(payload.data as AnalyzeResponse);
      return;
    }

    if (payload.stage === "error") {
      close();
      handlers.onError(payload.message || "流式分析失败");
      return;
    }

    handlers.onProgress(payload);
  };

  source.onerror = () => {
    if (closedByClient) {
      return;
    }
    close();
    handlers.onError("SSE 连接失败，请确认后端服务已启动");
  };

  return {
    close,
  };
}
