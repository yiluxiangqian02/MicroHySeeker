/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        status: {
          ok: "#1f8a4d",
          warning: "#b7791f",
          error: "#c53030",
          unknown: "#4a5568",
        },
      },
    },
  },
  plugins: [],
};

