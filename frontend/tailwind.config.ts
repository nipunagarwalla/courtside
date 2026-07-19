import type { Config } from "tailwindcss";

// Tailwind v4 works config-less; this file is here for future customization.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
