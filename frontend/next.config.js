/** @type {import('next').NextConfig} */
const pages = process.env.NEXT_PUBLIC_STATIC_ARCHIVE === "true";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
if (basePath && !/^\/[a-zA-Z0-9._-]+$/.test(basePath)) {
  throw new Error(
    "NEXT_PUBLIC_BASE_PATH must be empty or one repository path, without a trailing slash.",
  );
}
const nextConfig = pages
  ? {
      output: "export",
      basePath,
      trailingSlash: true,
      images: { unoptimized: true },
      webpack(config) {
        // Keep the local maintainer application out of the public static bundle.
        config.resolve.alias["@/components/ReviewStudio$"] = require.resolve(
          "./src/components/ArchiveAbout.tsx",
        );
        config.resolve.alias[require.resolve("./src/components/ReviewStudio.tsx")] =
          require.resolve("./src/components/ArchiveAbout.tsx");
        return config;
      },
    }
  : {
      output: "standalone",
      async rewrites() {
        return [
          {
            source: "/api/:path*",
            destination: `${process.env.BACKEND_URL || (process.env.NODE_ENV === "production" ? "http://api:8000" : "http://localhost:8000")}/api/:path*`,
          },
        ];
      },
    };

module.exports = nextConfig;
