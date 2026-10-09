"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

type ChartSize = { width: number; height: number };

/** Keep scientific run state mounted while omitting charts in collapsed or hidden panels. */
export function ChartFrame({
  label,
  children,
}: {
  label: string;
  children: (size: ChartSize) => ReactNode;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<ChartSize | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === "undefined") return;

    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      const width = Math.floor(entry.contentRect.width);
      const height = Math.floor(entry.contentRect.height);
      setSize((previous) => {
        if (width <= 0 || height <= 0) return null;
        if (previous?.width === width && previous.height === height) return previous;
        return { width, height };
      });
    });
    // ResizeObserver reports both disclosure visibility changes and window resizing.
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className="mt-4 h-72 min-w-0" aria-label={label}>
      {size ? children(size) : null}
    </div>
  );
}
