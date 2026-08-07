/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  agentRules: false,
  turbopack: {
    root: import.meta.dirname,
  },
};

export default nextConfig;
