import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        hot: "#ef4444",
        warm: "#f97316",
        cold: "#6b7280",
      },
    },
  },
  plugins: [],
};

export default config;
