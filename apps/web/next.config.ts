import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  agentRules: false,
  reactStrictMode: true,
  poweredByHeader: false,
  turbopack: { root: path.resolve(process.cwd(), "../..") },
  allowedDevOrigins: ["localhost", "127.0.0.1"],
  experimental: {
    optimizePackageImports: ["recharts"],
  },
};

export default nextConfig;
