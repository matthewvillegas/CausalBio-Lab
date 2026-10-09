import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createInvestigation,
  generateReport,
  interpretResearch,
  researchQuestion,
} from "@/lib/api";
import { investigationFixture } from "@/tests/fixture";
import { researchInterpretationFixture, researchResultFixture } from "@/tests/research-fixture";

describe("typed API client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends the default research interpretation and curated investigation context", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(researchInterpretationFixture), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(investigationFixture), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(interpretResearch("memory question")).resolves.toEqual(
      researchInterpretationFixture,
    );
    await expect(createInvestigation("memory question", { activity: "learning" })).resolves.toEqual(
      investigationFixture,
    );
    expect(fetchMock.mock.calls[0]?.[0]).toMatch(/\/api\/v1\/research\/interpret$/);
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      question: "memory question",
      depth: "research",
      online: true,
      context: {},
    });
    expect(fetchMock.mock.calls[1]?.[0]).toMatch(/\/api\/v1\/investigations$/);
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({
      question: "memory question",
      context: { activity: "learning" },
    });
  });

  it("preserves requested depth, offline mode and edited context through research requests", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify(researchInterpretationFixture)))
      .mockResolvedValueOnce(new Response(JSON.stringify(researchResultFixture)));
    vi.stubGlobal("fetch", fetchMock);
    const context = { tissue: "tendon", population: null, wants_interventions: false };
    await interpretResearch("tendon recovery", "deep", false);
    await expect(researchQuestion("tendon recovery", context, "deep", false)).resolves.toEqual(
      researchResultFixture,
    );
    expect(
      fetchMock.mock.calls.map(([url, init]) => ({
        path: new URL(String(url)).pathname,
        method: init?.method,
        body: JSON.parse(String(init?.body)),
      })),
    ).toEqual([
      {
        path: "/api/v1/research/interpret",
        method: "POST",
        body: { question: "tendon recovery", context: {}, depth: "deep", online: false },
      },
      {
        path: "/api/v1/research",
        method: "POST",
        body: { question: "tendon recovery", context, depth: "deep", online: false },
      },
    ]);
  });

  it("retains a structured problem's recovery options and correlation ID", async () => {
    const problem = {
      type: "about:blank",
      title: "More context needed",
      status: 422,
      detail: "Specify the biological outcome.",
      correlation_id: "problem-id",
      alternatives: ["long-term memory retention"],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response(JSON.stringify(problem), { status: 422 })),
    );
    await expect(interpretResearch("retention")).rejects.toMatchObject({
      name: "ApiError",
      message: problem.detail,
      problem,
    });
  });

  it.each([
    null,
    [],
    "upstream stack trace",
    { detail: "upstream stack trace" },
    {
      type: "about:blank",
      title: "Error",
      status: 500,
      detail: "upstream stack trace",
      correlation_id: "unsafe-id",
      alternatives: [42],
    },
    {
      type: "about:blank",
      title: "Error",
      status: "500",
      detail: "upstream stack trace",
      correlation_id: "unsafe-id",
      alternatives: [],
    },
    {
      type: "about:blank",
      title: "Error",
      status: 200,
      detail: "upstream stack trace",
      correlation_id: "unsafe-id",
      alternatives: [],
    },
  ])("falls back safely for malformed problem JSON: %j", async (body) => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response(JSON.stringify(body), {
          status: 500,
          headers: { "x-correlation-id": "safe-id" },
        }),
      ),
    );
    await expect(generateReport("investigation-id")).rejects.toMatchObject({
      name: "ApiError",
      problem: {
        title: "Request failed",
        status: 500,
        correlation_id: "safe-id",
        alternatives: [],
        detail: "The research service returned 500. Check that the local API is running.",
      },
    });
  });

  it("throws a structured ApiError without exposing arbitrary response text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response("upstream stack trace", {
          status: 500,
          headers: { "x-correlation-id": "safe-id" },
        }),
      ),
    );
    const error = await generateReport("investigation-id").catch((value: unknown) => value);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).problem.correlation_id).toBe("safe-id");
    expect((error as ApiError).message).not.toContain("stack trace");
  });
});
