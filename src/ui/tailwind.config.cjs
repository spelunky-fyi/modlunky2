const typography = require("@tailwindcss/typography");
const forms = require("@tailwindcss/forms");

function withOpacityValue(variable) {
  return ({ opacityValue }) => {
    if (opacityValue === undefined) {
      return `rgb(var(${variable}))`;
    }
    return `rgb(var(${variable}) / ${opacityValue})`;
  };
}

const config = {
  content: ["./src/**/*.{html,js,svelte,ts}"],

  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        theme: {
          50: withOpacityValue("--palette-base-50"),
          100: withOpacityValue("--palette-base-100"),
          200: withOpacityValue("--palette-base-200"),
          300: withOpacityValue("--palette-base-300"),
          400: withOpacityValue("--palette-base-400"),
          500: withOpacityValue("--palette-base-500"),
          600: withOpacityValue("--palette-base-600"),
          700: withOpacityValue("--palette-base-700"),
          800: withOpacityValue("--palette-base-800"),
          900: withOpacityValue("--palette-base-900"),
          primary: withOpacityValue("--theme-primary"),
          secondary: withOpacityValue("--theme-secondary"),
        },
      },
    },
  },

  plugins: [forms, typography],
};

module.exports = config;
