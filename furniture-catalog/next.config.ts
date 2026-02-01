
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
      {
        protocol: "https",
        hostname: "www.bomma.cz",
      },
      {
        protocol: "https",
        hostname: "*.bomma.cz",
      },
      {
        protocol: "https",
        hostname: "de-co-de.ru",
      },
      {
        protocol: "https",
        hostname: "*.de-co-de.ru",
      },
    ],
    // Fallback for older Next.js versions or specific cases
    domains: ['www.bomma.cz', 'bomma.cz', 'www.vandersanden.com', 'de-co-de.ru'],
    localPatterns: [
      {
        pathname: '/sites/**',
        search: '?itok=*',
      },
    ],
  },
};

export default nextConfig;
