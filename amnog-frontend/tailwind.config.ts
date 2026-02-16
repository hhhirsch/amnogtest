import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1218",
        bg2: "#161b24",
        surface: "#1e2535",
        surface2: "#252d3d",
        gold: "#e8b84b",
        "gold-dim": "rgba(232,184,75,0.15)",
        "gold-glow": "rgba(232,184,75,0.25)",
        ink: "#f0f2f7",
        "ink-soft": "#9ba4b8",
        "ink-muted": "#5a6378",
      },
      fontFamily: {
        serif: ["Instrument Serif"],
        sans: ["DM Sans"],
      },
    },
  },
  plugins: [],
};

export default config;
