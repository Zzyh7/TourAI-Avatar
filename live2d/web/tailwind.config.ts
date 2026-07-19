import type { Config } from "tailwindcss";
import { heroui } from "@heroui/react";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        buddhist: {
          gold: '#C9A24E',
          'gold-dark': '#8B6914',
          'gold-light': '#D4A853',
          brown: '#4A3028',
          'brown-deep': '#3E2723',
          cream: '#FFF9ED',
          parchment: '#FFFDF5',
          beige: '#E0D3C0',
          taupe: '#8B7355',
          saffron: '#E8A84C',
        },
      },
    },
  },
  darkMode: "class",
  plugins: [heroui()],
};
export default config;
