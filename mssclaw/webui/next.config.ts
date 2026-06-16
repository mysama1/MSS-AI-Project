import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  typescript: { ignoreBuildErrors: true },
  async redirects() {
    return [{ source: '/', destination: '/dashboard/overview', permanent: true }];
  },
};

export default nextConfig;