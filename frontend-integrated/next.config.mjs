/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,   // required for static export
  },
  // Uncomment 'output' only when building the APK (Capacitor needs static files)
  // For web deployment (Vercel/server) keep it commented out
  // output: 'export',
};

export default nextConfig;
