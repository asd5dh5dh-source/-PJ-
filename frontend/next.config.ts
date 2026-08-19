import type { NextConfig } from "next";

const apiBaseUrl = (
  process.env.VOC_API_BASE_URL?.trim() || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  // Next.js 16.3 currently fails Vercel's post-build step with standalone output.
  output: process.env.VERCEL ? undefined : "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
