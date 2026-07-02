import { describe, expect, it, vi } from "vitest";

import { analyzeRepo, analyzeRepoStream } from "./api";

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  emit(payload: unknown) {
    this.onmessage?.({
      data: JSON.stringify(payload),
    } as MessageEvent<string>);
  }
}

describe("analyzeRepo", () => {
  it("posts repo_url to the backend analyze endpoint", async () => {
    const responseBody = {
      repo_context: { owner: "langchain-ai", repo: "langgraph" },
      agents: {},
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => responseBody,
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await analyzeRepo("https://github.com/langchain-ai/langgraph");

    expect(result).toEqual(responseBody);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repo_url: "https://github.com/langchain-ai/langgraph",
      }),
    });
  });

  it("throws the backend detail when the request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: "Missing DASHSCOPE_API_KEY" }),
      }),
    );

    await expect(analyzeRepo("https://github.com/example/repo")).rejects.toThrow(
      "Missing DASHSCOPE_API_KEY",
    );
  });
});

describe("analyzeRepoStream", () => {
  it("opens the stream endpoint and forwards progress and done events", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.instances = [];
    const onProgress = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    const stream = analyzeRepoStream("https://github.com/langchain-ai/langgraph", {
      onProgress,
      onDone,
      onError,
    });
    const source = FakeEventSource.instances[0];

    expect(source.url).toBe(
      "http://localhost:8000/analyze/stream?repo_url=https%3A%2F%2Fgithub.com%2Flangchain-ai%2Flanggraph",
    );

    source.emit({
      stage: "code_audit",
      message: "Agent A 正在分析代码结构",
      data: null,
    });
    source.emit({
      stage: "done",
      message: "完成",
      data: {
        repo_context: { owner: "langchain-ai", repo: "langgraph" },
        agents: {},
      },
    });

    expect(onProgress).toHaveBeenCalledWith({
      stage: "code_audit",
      message: "Agent A 正在分析代码结构",
      data: null,
    });
    expect(onDone).toHaveBeenCalledWith({
      repo_context: { owner: "langchain-ai", repo: "langgraph" },
      agents: {},
    });
    expect(onError).not.toHaveBeenCalled();
    expect(source.closed).toBe(true);

    stream.close();
    expect(source.closed).toBe(true);
  });

  it("forwards error events and closes the stream", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.instances = [];
    const onError = vi.fn();

    analyzeRepoStream("https://github.com/example/repo", {
      onProgress: vi.fn(),
      onDone: vi.fn(),
      onError,
    });
    const source = FakeEventSource.instances[0];

    source.emit({
      stage: "error",
      message: "Missing DASHSCOPE_API_KEY",
      data: null,
    });

    expect(onError).toHaveBeenCalledWith("Missing DASHSCOPE_API_KEY");
    expect(source.closed).toBe(true);
  });

  it("does not replace a server error with the generic connection error", () => {
    vi.stubGlobal("EventSource", FakeEventSource);
    FakeEventSource.instances = [];
    const onError = vi.fn();

    analyzeRepoStream("https://github.com/example/repo", {
      onProgress: vi.fn(),
      onDone: vi.fn(),
      onError,
    });
    const source = FakeEventSource.instances[0];

    source.emit({
      stage: "error",
      message: "DashScope request failed",
      data: null,
    });
    source.onerror?.();

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith("DashScope request failed");
  });
});
