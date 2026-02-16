import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f172a",
        ink: {
          DEFAULT: "#e2e8f0",
          muted: "#94a3b8",
          soft: "#cbd5e1",
        },
        gold: {
          DEFAULT: "#e8b84b",
          dark: "#1a1206",
          50: "#FDF8E8",
          100: "#FAF0D1",
          200: "#F5E1A3",
          300: "#F0D275",
          400: "#EBC347",
          500: "#e8b84b",
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
    },
  },
  plugins: [],
};

export default config;
