import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: '/', destination: '/dashboard/overview', permanent: true },
    ];
  },
};

export default nextConfig;
