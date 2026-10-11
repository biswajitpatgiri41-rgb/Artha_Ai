import path from 'node:path';

/** @type {import('next').NextConfig} */
const nextConfig = {
	// Keep standalone output tracing scoped to this app despite the parent
	// workspace containing unrelated package lockfiles.
	outputFileTracingRoot: path.resolve(import.meta.dirname),
};

export default nextConfig;
