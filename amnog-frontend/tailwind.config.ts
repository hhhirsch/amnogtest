import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f172a",
        ink: "#e2e8f0",
        surface: "#1e293b",
        "ink-soft": "#cbd5e1",
        "ink-muted": "#94a3b8",
        gold: {
          DEFAULT: "#C9A227",
          50: "#FDF8E8",
          100: "#FAF0D1",
          200: "#F5E1A3",
          300: "#F0D275",
          400: "#EBC347",
          500: "#C9A227",
          600: "#A1821F",
          700: "#796217",
          800: "#514110",
          900: "#292108",
        },
      },
      fontFamily: {
        sans: ['"DM Sans"', 'sans-serif'],
        serif: ['"Instrument Serif"', 'serif'],
      },
      transitionDuration: {
        '250': '250ms',
      },
    },
  },
  plugins: [],
};

export default config;
