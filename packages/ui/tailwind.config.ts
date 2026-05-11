import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#101820",
        ink: "#ecf2f8",
        muted: "#8ba0b5",
        line: "#243442",
        ox: "#ff9f1c",
        gene: "#47a3ff",
        protein: "#56d364",
        disease: "#ff5d73",
        metabolite: "#f9d65c"
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,255,255,0.06), 0 18px 60px rgba(0,0,0,0.28)"
      }
    }
  },
  plugins: []
};

export default config;
