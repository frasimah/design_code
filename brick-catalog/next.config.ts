
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "www.vandersanden.com",
      },
      {
        protocol: "https",
        hostname: "*.vandersanden.com",
      },
    ],
    localPatterns: [
      {
        pathname: '/sites/**',
        search: '?itok=*',
      },
    ],
  },
};

export default nextConfig;
