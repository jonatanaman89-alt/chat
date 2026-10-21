/** @type {import('next').NextConfig} */

// Security headers (next.config.js headers()). Vercel adds only Strict-Transport-Security.
//   • Every response: X-Content-Type-Options: nosniff (a file is only ever used as the type
//     it's served as) and Referrer-Policy: strict-origin-when-cross-origin (other sites see
//     our origin, never a full URL with ?next=… or a share link's bot id).
//   • Every PAGE except the ones meant for other sites: no framing — X-Frame-Options: DENY
//     plus CSP frame-ancestors 'none' (the modern form) — so the login, the sign-up, the app
//     (billing, delete bot, integrations) and the password reset can't be clickjacked inside
//     another site's <iframe>. Plus Permissions-Policy: no camera, microphone or location
//     (nothing here uses them).
//   Left frameable: /chat (a customer's share link — a customer may want to frame it),
//   /widget.js and /api/* (called from customers' sites; the frame headers mean nothing on
//   a script or JSON anyway). widget.js itself never frames our pages (it renders in a
//   Shadow DOM on the customer's page).
// A full script-src CSP would need nonces for the root layout's inline <html lang> script
// (lib/routes.js HTML_LANG_SCRIPT), so this starts with frame-ancestors only.
const COMMON_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
];
const NO_FRAMING_HEADERS = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];
// Every path except /chat (and /chat/…), /api/… and /widget.js.
const NO_FRAMING_SOURCE = "/((?!chat(?:/|$)|api/|widget\\.js$).*)";

const nextConfig = {
  reactStrictMode: true,
  // No technology fingerprint ("X-Powered-By: Next.js") on page responses.
  poweredByHeader: false,
  // GCP_LOCATION — the Google Cloud location the bots' AI runs in when
  // NEXT_PUBLIC_AI_PROVIDER=vertex (e.g. "eu"). Not a secret. Inlined at build time into the
  // server AND browser bundles (like a NEXT_PUBLIC_ variable) because the pages that say WHERE
  // the answers are generated — the privacy policy, the terms, the landing page (a client
  // component) — must name the same place the server calls (lib/aiProviderInfo.js vertexPlace),
  // with ONE variable for the owner to set. Unset → "" → the default "eu".
  // PUBLIC_APP_URL — the site's public address (https://…, no secret). Inlined for the same
  // reason: the app's copy-out links (embed code, share link — lib/publicOrigin.js) must use
  // the same host as the server's links (lib/integrations/http.js publicOrigin, Stripe's
  // return URLs, e-mails). Unset → "" → NEXT_PUBLIC_DOMAIN, then the Vercel domain.
  env: {
    GCP_LOCATION: process.env.GCP_LOCATION || "",
    PUBLIC_APP_URL: process.env.PUBLIC_APP_URL || "",
  },
  async headers() {
    return [
      { source: "/:path*", headers: COMMON_HEADERS },
      { source: NO_FRAMING_SOURCE, headers: NO_FRAMING_HEADERS },
    ];
  },
};

module.exports = nextConfig;
