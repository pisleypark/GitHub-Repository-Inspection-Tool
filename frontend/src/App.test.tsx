import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";
import { analyzeRepo, analyzeRepoStream } from "./api";

vi.mock("./api", () => ({
  analyzeRepo: vi.fn(),
  analyzeRepoStream: vi.fn(),
}));

const reportResponse = {
  repo_context: {
    owner: "langchain-ai",
    repo: "langgraph",
    stars: 100,
    forks: 20,
    languages: { Python: 1234, TypeScript: 456 },
  },
  agents: {
    code_auditor: {
      score: 82,
      strengths: ["包含测试"],
      risks: ["CI 配置较少"],
      suggestions: ["补充工程文档"],
    },
    product_analyst: {
      score: 78,
      readme_clarity: "README 清晰",
      open_source_activity: "活跃",
      strengths: ["定位明确"],
      risks: [],
      suggestions: ["补充案例"],
    },
    final_judge: {
      final_score: 80,
      level: "B",
      summary: "整体质量较好。",
      dimension_scores: {
        code_quality: 82,
        product_value: 78,
        activity: 80,
      },
      top_issues: ["CI 覆盖不足"],
      top_suggestions: ["补充使用示例"],
    },
  },
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("App", () => {
  it("submits a repo URL and renders the report", async () => {
    vi.stubGlobal("EventSource", function EventSource() {});
    vi.mocked(analyzeRepoStream).mockImplementation((_repoUrl, handlers) => {
      handlers.onProgress({
        stage: "parsing_url",
        message: "正在解析 GitHub URL",
        data: null,
      });
      handlers.onProgress({
        stage: "code_audit",
        message: "Agent A 正在分析代码结构",
        data: null,
      });
      setTimeout(() => handlers.onDone(reportResponse), 0);
      return { close: vi.fn() };
    });
    render(<App />);

    await userEvent.type(
      screen.getByLabelText("GitHub 仓库 URL"),
      "https://github.com/langchain-ai/langgraph",
    );
    await userEvent.click(screen.getByRole("button", { name: "开始体检" }));

    expect(screen.getByText("正在解析 GitHub URL")).toBeInTheDocument();
    expect(screen.getByText("Agent A 正在分析代码结构")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("langchain-ai/langgraph")).toBeInTheDocument();
    });
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("代码审计 Agent")).toBeInTheDocument();
    expect(screen.getByText("产品价值 Agent")).toBeInTheDocument();
    expect(screen.getByText("最终裁判 Agent")).toBeInTheDocument();
    expect(screen.getByText("整体质量较好。")).toBeInTheDocument();
  });

  it("shows a validation error for empty input", async () => {
    vi.mocked(analyzeRepo).mockResolvedValue(reportResponse);
    vi.mocked(analyzeRepoStream).mockReturnValue({ close: vi.fn() });
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "开始体检" }));

    expect(screen.getByText("请输入 GitHub 仓库 URL")).toBeInTheDocument();
  });
});
