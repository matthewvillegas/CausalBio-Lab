import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChartFrame } from "@/components/charts/ChartFrame";

afterEach(() => vi.unstubAllGlobals());

describe("ChartFrame", () => {
  it("renders only at positive measured sizes, removes hidden charts, and restores them when reopened", () => {
    let notifyResize!: ResizeObserverCallback;
    const observe = vi.fn();
    const disconnect = vi.fn();
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: ResizeObserverCallback) {
          notifyResize = callback;
        }
        observe = observe;
        disconnect = disconnect;
      },
    );
    const view = render(
      <ChartFrame label="Test chart">
        {({ width, height }) => (
          <output>
            {width} × {height}
          </output>
        )}
      </ChartFrame>,
    );
    const container = screen.getByLabelText("Test chart");
    expect(observe).toHaveBeenCalledWith(container);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    const resize = (width: number, height: number) =>
      act(() => {
        notifyResize(
          [
            {
              target: container,
              contentRect: new DOMRectReadOnly(0, 0, width, height),
              borderBoxSize: [{ inlineSize: width, blockSize: height }],
              contentBoxSize: [{ inlineSize: width, blockSize: height }],
              devicePixelContentBoxSize: [{ inlineSize: width, blockSize: height }],
            },
          ],
          { observe, disconnect, unobserve: vi.fn() },
        );
      });
    resize(0, 0);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    resize(640.9, 288);
    expect(screen.getByRole("status")).toHaveTextContent("640 × 288");
    resize(0, 0);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    resize(320, 288);
    expect(screen.getByRole("status")).toHaveTextContent("320 × 288");
    resize(320, 0);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    view.unmount();
    expect(disconnect).toHaveBeenCalledOnce();
  });
});
