import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    // Browsers call the website origin; only Next.js talks to the API host.
    const apiOrigin = (process.env.API_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    return [
      { source: "/api/v1/:path*", destination: `${apiOrigin}/api/v1/:path*` },
    ];
  },
};

export default nextConfig;
