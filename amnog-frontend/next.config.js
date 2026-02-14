const repo = "amnogtest";
const isPages = process.env.DEPLOY_TARGET === "gh-pages";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: isPages ? "export" : undefined, // Vercel: normales Next build
  images: { unoptimized: true },
  trailingSlash: true,

  basePath: isPages ? `/${repo}` : "",
  assetPrefix: isPages ? `/${repo}/` : undefined,
};

module.exports = nextConfig;