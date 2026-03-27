import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "bleu-marine": "#1B3A5C",
        "vert-sauge": "#4A7C59",
        "creme": "#F8F7F4",
      },
      fontFamily: {
        playfair: ["var(--font-playfair)", "Georgia", "serif"],
        source: ["var(--font-source)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
