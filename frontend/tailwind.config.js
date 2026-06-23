/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#1D9E75",
          light: "#E1F5EE",
          dark: "#085041",
        },
        coles: "#E24B4A",
        woolworths: "#639922",
        iga: "#EF9F27",
      },
    },
  },
  plugins: [],
};
