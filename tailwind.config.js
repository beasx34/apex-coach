/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./overlay.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        apex: {
          red: "#ED1C24",
          dark: "#0F0F12",
          mid: "#191920",
          light: "#2A2A35",
          accent: "#FFB700",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
