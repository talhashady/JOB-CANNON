import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05060a",
          900: "#0a0c14",
          800: "#111524",
          700: "#1a1f33",
        },
        neon: {
          violet: "#8b5cf6",
          fuchsia: "#d946ef",
          cyan: "#22d3ee",
          lime: "#a3e635",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-grotesk)", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "aurora": "radial-gradient(60% 60% at 50% 0%, rgba(139,92,246,0.25) 0%, rgba(5,6,10,0) 70%), radial-gradient(40% 40% at 80% 20%, rgba(34,211,238,0.18) 0%, rgba(5,6,10,0) 70%), radial-gradient(50% 50% at 20% 30%, rgba(217,70,239,0.18) 0%, rgba(5,6,10,0) 70%)",
        "grid": "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
      },
      backgroundSize: {
        "gridcell": "48px 48px",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,255,255,0.06), 0 20px 60px -20px rgba(139,92,246,0.45)",
        "glow-cyan": "0 0 0 1px rgba(255,255,255,0.06), 0 20px 60px -20px rgba(34,211,238,0.45)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-12px)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "gradient-x": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        shimmer: "shimmer 2s infinite",
        "gradient-x": "gradient-x 8s ease infinite",
      },
    },
  },
  plugins: [],
};

export default config;
