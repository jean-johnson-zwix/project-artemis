import type { NextConfig } from "next";
import * as dotenv from "dotenv";
import * as path from "path";

// Load the root .env so local dev works without a data-explorer/.env file.
// Next.js only reads from the project root (data-explorer/) by default.
// If data-explorer/.env exists it takes precedence (loaded afterwards by Next.js).
dotenv.config({ path: path.resolve(process.cwd(), "../.env"), override: false });

const nextConfig: NextConfig = {};

export default nextConfig;
