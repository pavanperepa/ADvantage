import path from "node:path";
import type { NextConfig } from "next";

const backendHostPort = process.env.BACKEND_INTERNAL_HOSTPORT;
const backendOrigin = (
  process.env.BACKEND_INTERNAL_URL ??
  (backendHostPort ? `http://${backendHostPort}` : "http://127.0.0.1:8000")
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  // The worktree root (one level up) has its own package-lock.json and a
  // node_modules symlink pointing outside this worktree entirely (shared
  // with the sibling ADvantage checkout). Without an explicit root,
  // Turbopack infers that outer directory as the workspace root and then
  // fails trying to resolve through that symlink. Pinning the root to this
  // frontend/ directory keeps dependency resolution scoped to its own,
  // locally-installed node_modules.
  turbopack: {
    root: path.join(__dirname),
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
