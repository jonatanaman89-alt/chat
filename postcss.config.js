// NOTE: Tailwind v4 is installed, which moved its PostCSS plugin to a separate
// package (`@tailwindcss/postcss`) and changed the CSS entry syntax. The product
// styles with CSS variables + inline styles (see ADR-002), not Tailwind utilities,
// so we run with no PostCSS plugins — the known-good config that deploys on Vercel.
// The `@tailwind` directives in globals.css are harmless no-ops without the plugin.
// Properly activating Tailwind v4 is a separate P1 task in TASKS.md.
module.exports = {
  plugins: {},
};
