import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070A14",
          900: "#0B1020",
          850: "#10182D",
          800: "#13203A",
          700: "#1D3158",
        },
        accent: {
          cyan: "#1BC5FF",
          blue: "#4F7CFF",
          magenta: "#D44CFF",
          green: "#33E9A5",
          orange: "#FFAE57",
          red: "#FF6B7A",
        },
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(79,124,255,.2), 0 12px 28px rgba(7,10,20,.5)",
        soft: "0 8px 24px rgba(7,10,20,.35)",
      },
      borderRadius: {
        xl2: "1rem",
      },
      backgroundImage: {
        noise:
          "radial-gradient(circle at 20% 10%, rgba(27,197,255,.12), transparent 30%), radial-gradient(circle at 80% 0%, rgba(212,76,255,.12), transparent 32%), radial-gradient(circle at 50% 100%, rgba(79,124,255,.12), transparent 30%)",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
