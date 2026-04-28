/** @type {import('next').NextConfig} */
const isDemo = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
const repoBase = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig = isDemo
  ? {
      output: "export",
      basePath: repoBase,
      assetPrefix: repoBase || undefined,
      images: { unoptimized: true },
      trailingSlash: true,
    }
  : {
      async rewrites() {
        return [
          {
            source: "/api/:path*",
            destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/api/:path*`,
          },
        ];
      },
    };

module.exports = nextConfig;
