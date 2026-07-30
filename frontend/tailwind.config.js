/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#10211c",
        mist: "#eef3ee",
        fern: "#226f54",
        lime: "#c8ff7c",
        coral: "#ff7a59",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Manrope", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        panel: "0 24px 70px rgba(16, 33, 28, 0.12)",
      },
    },
  },
  plugins: [],
};

