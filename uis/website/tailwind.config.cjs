module.exports = {
  content: [
    "./uis/website/index.html",
    "./uis/website/application.html",
    "./uis/website/shared-components.js"
  ],
  safelist: ["border-rose-400", "focus-visible:ring-rose-300"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Manrope", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      colors: {
        brand: {
          50: "#f5f8ff",
          100: "#e8efff",
          300: "#98b2ff",
          500: "#3458d6",
          700: "#1f378f",
          900: "#0f1b45"
        }
      }
    }
  },
  plugins: []
};
