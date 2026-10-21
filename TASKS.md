# TASKS — MVP innan produkten kan säljas

Prioriterad lista. **P0 = blockerar all försäljning** (utan dessa kan en betalande kund
inte använda produkten på ett säkert/fungerande sätt). P1 = krävs för en trovärdig
kommersiell lansering. P2 = polish efter lansering.

Status: `[ ]` ej påbörjad · `[~]` påbörjad · `[x]` klar

> **Statusavstämning mot koden 2026-09-02.** En fullständig end-to-end-testkampanj (UI, publika
> API:er, ägar-API:er, billing, pipeline, ärlighet i texter) verifierade varje kryss nedan mot
> faktisk kod och dev-server. Alla ursprungliga P0-blockerare utom tokenkvoten är stängda.
> Se ADR-011 i `DECISIONS.md`. Manuella steg som bara Jonatan kan göra finns längst ner.
>
> **Statusavstämning 2026-09-30.** Integrationerna är ombyggda: alla 15 i
> `src/lib/integrations/catalog.js` är byggda (inga ”kommer snart” kvar), med tillstånd i
> `bots.config.integrations` (ADR-012). Produktionen har dem först efter nästa deploy (repot saknar
> git-remote). **Anthropic-kontot saknar kredit — ingen bot svarar med AI förrän det är påfyllt.**
> De nya manuella stegen står överst under ”Manuella steg för Jonatan”.

---

## P0 — Blockerare (måste lösas före första betalande kund)

- [x] **Riktig databas (Supabase Postgres).** ✔ 2026-09-02 — `src/app/page.jsx` läser/skriver
  bots via `botStore.js` (`listBots`/`saveBot`/`deleteBotById`), profil via `profileStore.js`,
  plan från `subscriptions`. Schema med RLS för profiles, bots, subscriptions, leads, usage,
  conversations, processed_webhook_events, integration_interests i `supabase/schema.sql`
  (applicerat live). `localStorage` är nu bara offline-cache per användare + byggarens testchattar.
- [x] **Säker autentisering.** ✔ 2026-09-02 — Supabase Auth (`AuthPage.jsx`: `signUp` /
  `signInWithPassword`, e-postbekräftelse, glömt/återställ lösenord med global utloggning),
  server-side session via `middleware.js` + `supabase/server.js`. Lösenordspolicy min 8 +
  blocklista (`passwordPolicy.js`). localStorage-"konton" och den gamla hash-koden är borttagna;
  offline-cachen är per användare och rensas helt vid utloggning.
- [x] **Fungerande embed-widget.** ✔ 2026-09-02 — `public/widget.js` serveras från appens egen
  origin; embed-koden byggs från `window.location.origin` (`EmbedPage.jsx`). Widgeten hämtar
  config från `/api/bot/[id]`, chattar via `/api/chat/[id]` (SSE), skickar leads till `/api/lead`,
  följer byggarens position/utseende/mobil-fullscreen och visar "inte tillgänglig" om boten
  saknas/är avstängd. Verifierat cross-origin från annan port.
- [x] **Server-side bot-/kunskaps-API för widgeten.** ✔ 2026-09-02 — widget och `/chat?bot=<id>`
  använder `/api/bot` + `/api/chat` (ingen base64-i-URL). `/api/bot` svarar med allowlistade
  fält (ingen kunskapsbas, inga webhook-hemligheter), cache 5 min.
- [x] **Koppla Stripe-betalning till faktisk plan (entitlement).** ✔ 2026-09-02 — plan sätts
  server-side från signerad webhook (bara vid `payment_status === "paid"`), `checkout/verify`
  upsertar idempotent, appen **läser** planen från `subscriptions` och enforce:ar: bot-tak i
  DB-trigger, konversationstak + trial-utgång (14 d) i `/api/chat`. Planbyte uppdaterar
  befintlig prenumeration med proration; kundportal via `/api/portal`.
- [x] **Verifiera Stripe-webhook-signatur.** ✔ 2026-07-01 — `verifyStripeSignature()` (HMAC-SHA256,
  replay-skydd 300 s, konstant-tids-jämförelse), fail-closed utan `STRIPE_WEBHOOK_SECRET`.
  2026-09-02: dessutom idempotens via `processed_webhook_events` (markeras EFTER lyckad apply).
- [x] **Skydda `/api/ai` (öppen proxy).** ✔ 2026-07-01 — `sameOriginOk()` + `rateLimit()` först i
  handlern. 2026-09-02: samma mönster på `/api/crawl` (+ SSRF-guard), health-routes admin-only.
- [ ] **Riktig token-/användningskvot per användare.** Konversationstaket per plan enforce:as nu
  (atomisk `increment_usage`), men AI-tokenbudgeten delas fortfarande globalt och rate-limit-
  storen i `apiGuard.js` är in-memory (nollställs vid cold start på serverless). Flytta till
  delad store (Upstash/Redis) och inför per-användar-/per-bot-tokenmätning med tak.
  `/api/crawl` och `/api/ai` bör dessutom kräva inloggning (Origin-gaten stoppar inte curl).
- [ ] **Vercel Deployment Protection AV.** Produktionen (`chatbot-app-828.vercel.app`) svarar
  401 "Protected deployment" för anonyma anrop → widget, delningslänk, Stripe-webhook och
  kanalernas webhooks (Telegram/Meta → `/api/channels/…`) fungerar inte förrän det är avstängt
  (manuellt steg nedan).
- [ ] **AI-kredit hos Anthropic.** Kontot är tomt (2026-09-30) → varje bot svarar med ett vänligt
  felmeddelande i widget, delningslänk och kanaler (syns som varning per bot på Dashboard och
  som AI-status i Admin). Manuellt steg nedan — eller byt till OpenAI (”Byta AI-leverantör”).
- [~] **Ta bort hemligheter ur repo.** `sabba.txt`, `sabba.db`, `sessions/` ligger kvar i
  projektroten men är gitignorerade (inte committade). Återstår: radera dem från disk och
  rotera ev. exponerade nycklar. Repot saknar dessutom git-remote.
  2026-10-09 (CH-03/CH-07): inga lösenord kvar i spårade filer — seed-skripten tar `SEED_PASSWORD`
  eller slumpar ett starkt lösenord som visas en gång, `check-*.mjs` läser `SEED_PASSWORD`, och
  seed-skripten vägrar köra mot produktionsdatabasen utan `--i-know-this-is-production`. De gamla
  lösenorden finns kvar i git-historiken → byt dem (se ”Konton och demo”).
- [x] **Lanseringsspärr för betalningar (OPS-10/CL-05).** ✔ 2026-10-09 — `src/lib/checkoutGate.js`:
  Checkout är öppen med live-nyckel, eller med testnyckel utanför produktion (`next dev`, testerna).
  Testnyckel i produktion (`NODE_ENV=production`/`VERCEL_ENV=production|preview`) = stängt utan
  `STRIPE_ALLOW_TEST_MODE=1`; `STRIPE_CHECKOUT_ENABLED=false` = nödbroms i alla lägen. Stängt:
  `/api/checkout` 503 `checkout_closed`, appen visar ”Betalning öppnar snart” med knapparna
  avstängda, verify/portal 503 med testnyckel i produktion, webhooken ignorerar event från fel läge
  (livemode). Admin visar läget i kortet ”Betalningar (Stripe)”. Se README ”Betalningar: lanseringsspärr”.

## P1 — Krävs för trovärdig kommersiell lansering

- [ ] **Juridisk granskning.** `/integritetspolicy` och `/villkor` finns som **utkast** (banner
  "låt jurist granska") med platshållare för företagsnamn, org.nr, adress, tingsrätt,
  lagringstid och DPA. Fyll i, verifiera överföringsmekanism för USA-leverantörer
  (Anthropic, Stripe, Vercel: SCC/DPF), låt jurist granska, ta bort bannern. Cookie-samtycke
  behövs bara om spårningscookies införs (idag bara sessionscookies). Sedan 2026-09-30 finns
  också integrationsstycken i båda texterna (kanaler, notiser/ärenden, LiveChat, butikssynk) —
  se ”Gör först” nedan.
- [ ] **Stripe-konfiguration (manuellt).** Stripe Tax (priserna visas "exkl. moms" tills dess),
  produktnamn Starter/Growth/Pro (idag Nybörjare/Pro/Max pro), publikt företagsnamn,
  kundportal aktiverad i live-läge, extra webhook-events, Klarna (valfritt). Se listan nedan.
- [ ] **Riktig besöksspårning (valfritt).** Leads-sidan visar bara besökare som lämnat
  kontaktuppgifter; anonyma besökare spåras inte (och sidan säger det). Vill vi ha
  besöksstatistik krävs en händelselogg från widgeten + cookie-samtycke.
- [ ] **Team/flera användare per företagskonto** (org-modell + roller). Alla plan-texter om
  "teammedlemmar" är borttagna tills detta finns.
- [ ] **Felhantering & observability.** Error boundaries i React, strukturerad server-loggning,
  Sentry/loggning. (Debug-loggarna är borttagna 2026-09-02.)
- [ ] **Höj max_tokens-taket i `src/lib/anthropic.js`** (`streamAnthropic` cappar på 4096 medan
  `/api/ai` och scanningen begär 8192). Trunkering hanteras redan med salvage + resume, men
  passen blir kortare än avsett.
- [x] **Stäng DNS-rebinding-luckan i SSRF-guarden.** ✔ 2026-09-30 — `guardedFetch` i `ssrf.js`
  (undici Agent / node:http med `guardedLookup`) kontrollerar adresserna när anslutningen öppnas;
  används av `crawl`, `webhook.js` och integrationernas `safeFetch`.
- [ ] **Migrera till TypeScript** (målstacken). Hela `src` är idag `.jsx` utan typer.
- [ ] **Tailwind: aktivera på riktigt eller stryk.** Dokumentationen säger nu "inline-styles"
  (sant). Om Tailwind ska in: v4 kräver `@tailwindcss/postcss` + `@import "tailwindcss"`.
- [x] **Aktivera riktiga integrationer.** ✔ 2026-09-02: 4 live (widget, WordPress, webhook,
  Zapier). ✔ 2026-09-30: alla 15 byggda — hemsida, WordPress, Shopify + WooCommerce (produktsynk
  till kunskapsbasen), Telegram/WhatsApp/Messenger/Instagram (boten svarar i kanalen),
  Slack/Discord (notiser), Zendesk/Freshdesk (ärenden), LiveChat (överlämning), webhook, Zapier.
  Ny integrationssida (kategorier, sök, detaljsida per integration), `/api/integrations`,
  `/api/channels/<provider>/<botId>`, `dispatch.js`, krypterade hemligheter (ADR-012).
  ”Kommer snart”/”Meddela mig” är borttaget; `integration_interests` finns kvar som historik i Admin.
  Kvar: driftsättning och kanalinställningar hos Telegram/Meta (manuella steg nedan).
- [x] **Enforce plan-gränser.** ✔ 2026-09-02 — bot-tak i DB-trigger `bots_enforce_limit`,
  konversationstak + trial-utgång i `/api/chat`, statuspolicy active/trialing/past_due.
  Kvar: pausa överskjutande bots vid nedgradering (idag förblir de aktiva).
- [x] **Riktig fakturering & kundportal.** ✔ 2026-09-02 — `/api/portal` + "Hantera prenumeration"
  i Fakturering, användningsmätare från `usage`, trial-/takbanners.
- [x] **Riktig analytics-/leads-data.** ✔ 2026-09-02 — Dashboard/Analys läser `usage` +
  `conversations` (RLS), Arkiv visar DB-samtal + lokala testchattar separat, Visitors → "Leads"
  utan falska tabbar/filter.
- [x] **Debug-loggar borttagna.** ✔ 2026-09-02 — bara server-side `[timing]`-loggar kvar.

## P2 — Polish efter lansering

- [ ] Onboarding/produkt-tour för nya kunder.
- [ ] A/B-test av bot-svar, leadkvalificering, e-postnotiser vidare till säljare.
- [ ] Flerspråkig widget (auto-detektera besökarens språk).
- [ ] Automatisk omscanning av kundens sajt (t.ex. var 6:e timme) för färskt lager/innehåll;
  "Scanna om"-hint i byggaren för bots scannade före pipeline-ändringarna 2026-09-02.
- [ ] Enhets-/integrationstester i repo + CI (kampanjens skript ligger i scratchpad, inte i repot).
- [ ] Flytta integrationstillståndet från `bots.config.integrations` till en egen tabell när någon
  av utlösarna i ADR-012 inträffar (många statusskrivningar per bot, frågor över alla botar,
  händelselogg/omförsök, en delad Meta-app för flera botar).
- [ ] `darkMode`-fältet i bot-config sparas utan UI-kontroll och ignoreras av widgeten — lägg
  till toggle eller ta bort fältet.
- [ ] `subscriptions.started_at` för exaktare MRR-trend i adminpanelen (idag `updated_at`).
- [ ] Sidebar: "Besökare" → "Leads"; ta bort dubbletten Dashboard/Chatbots.
- [ ] `src/lib/ai.js` returnerar fortfarande `_scrapedPages` i minnet (strippas vid spar) — håll
  dem utanför kunskapsobjektet.
- [x] Städa bort legacy `src/app/api/fetch/route.js`. ✔ 2026-09-02 — raderad, `crawl` ersätter.
- [ ] Ta bort orelaterade filer i repo-roten (`plat_mm.py`, `plat_1500x1300_mm.png`,
  `widget-test.html`, undermappen `vardagsschema/`) eller flytta till egna repon.
- [ ] **Uppgradera Next.js 14.2 → 15.5.x** (planera strax före eller efter lanseringen, inte i
  samma deploy). 14.x får inga säkerhetsfixar längre; `npm audit --omit=dev` (2026-10-08) visar 1
  kritisk + 3 höga utan fix på 14-linjen — de som gäller oss: RSC-DoS och cache-förgiftning
  (RSC-svar, middleware-redirects). 15.5 kräver React 19 och gör `cookies()`, `headers()` och
  `params` asynkrona (lib/serverLocale.js, lib/supabase/server.js, route-handlers med params).
  Kör hela testsviten och klickrundan efteråt.
- [ ] Språkvård (beslut, inte fel): "scanna/scanning" används i hela appen och på webbplatsen;
  Språkrådet rekommenderar "skanna". Byt i så fall överallt samtidigt (webbplats, app, mejl).

---

## Manuella steg för Jonatan (samlade från fix-rapporterna 2026-09-02, uppdaterade 2026-09-30)

### Gör först (nytt 2026-09-30)
- [ ] **Fyll på Anthropic-krediten.** console.anthropic.com → Plans & Billing. Kontot är tomt, så
  varje bot svarar just nu med ett felmeddelande (”Ett ögonblick — jag hade svårt att svara just
  nu …”) i widget, delningslänk och alla kanaler; inga samtal räknas eller sparas under tiden.
  Överväg att slå på automatisk påfyllning (auto-reload) på samma sida så det inte händer igen.
  Kontroll: Admin → AI-status (live-kontrollen mot Anthropic) ska visa OK; Dashboard-varningen per
  bot försvinner när boten svarat rätt igen.
- [ ] **Byta AI-leverantör (valfritt, i stället för påfyllningen ovan).** Koden kan köra OpenAI i
  stället för Anthropic — AVSTÄNGT tills du slår på det:
  1. Skapa en API-nyckel på platform.openai.com och fyll på krediter (Settings → Billing).
  2. `.env.local`: `OPENAI_API_KEY=…` och `NEXT_PUBLIC_AI_PROVIDER=openai`, starta om `npm run dev`.
  3. Vercel → Settings → Environment Variables: samma två, sedan **Redeploy** (variabeln bakas in
     vid bygget). Valfritt: `OPENAI_CHAT_MODEL`, `OPENAI_SCAN_MODEL` (standard `gpt-6.1-sol`).
  4. Kontroll: Admin → AI-status visar OpenAI och OK; ställ en fråga i widgeten.
  Integritetspolicyn, villkoren och startsidan säger då automatiskt ”OpenAI (USA)” — meddela
  kunderna om bytet av underbiträde och uppdatera datumet i policyn. Tillbaka: ta bort variabeln
  och deploya igen. Detaljer: README → ”Byta AI-leverantör”.
- [ ] **Stäng av Deployment Protection** (Vercel → Settings → Deployment Protection) — krävs för
  att widget, delningslänk, `/api/webhook` (Stripe) och kanalernas webhooks
  (`/api/channels/…`, anropas av Telegram och Meta) ska nå appen. Med skyddet på får de 401 och
  varken betalningar eller kanalmeddelanden kommer fram.
- [ ] **`PUBLIC_APP_URL` i Vercel** = produktionens https-origin, t.ex.
  `https://chatbot-app-828.vercel.app` (eller egen domän). Kanalernas
  Callback-URL (`<PUBLIC_APP_URL>/api/channels/<kanal>/<botId>`) byggs av den. Behövs inte i
  `.env.local` — från localhost sparas en kanal som ”väntar” och aktiveras med ”Uppdatera” på den
  publika adressen. (Saknas variabeln används `NEXT_PUBLIC_DOMAIN`, sedan Vercels produktionsdomän.)
- [ ] **`INTEGRATIONS_ENC_KEY` (valfritt men rekommenderat) — samma värde lokalt och i Vercel.**
  Den krypterar integrationernas tokens/nycklar. Lokalt och produktion använder **samma
  Supabase-databas**, så en koppling som sparas i den ena miljön måste kunna läsas i den andra:
  med olika nycklar visar den andra sidan ”anslut igen”, och i produktion avvisas då kanalernas
  meddelanden (Telegram/Meta får 401, boten är tyst). Gör så här: skapa en nyckel med
  `node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"`, lägg samma värde i
  `.env.local` och i Vercel (Production, Preview och Development), låt `SUPABASE_SECRET_KEY` ligga
  kvar i båda (äldre värden öppnas med den och krypteras om när kopplingen används eller sparas),
  starta om `npm run dev` och deploya. Byt eller ta aldrig bort nyckeln i bara en miljö. Utan egen
  nyckel krypteras med Supabase-nyckeln — kontrollera då att Vercel har samma `SUPABASE_SECRET_KEY`
  som `.env.local` (har Vercel bara `SUPABASE_SERVICE_ROLE_KEY` blir nycklarna olika).
- [ ] **Deploya den nya koden** (`vercel --prod`; repot saknar git-remote) och testa
  integrationerna med ett konto som har **Growth eller Pro** (även adminkontot räknas som trial för
  Growth-integrationerna om det saknar prenumeration).
- [ ] **Kanaler — vad som krävs per kanal** (öppna Integrationer på den publika adressen när du
  ansluter; en Meta-app kan bara skicka webhooks till en bot per kanal):
  - **Telegram:** automatiskt. Token från @BotFather → ”Anslut” — webhooken registreras direkt.
    Boten svarar i privata chattar (grupper ignoreras). Ansluten från localhost = ”väntar” → klicka
    ”Uppdatera” på den publika adressen.
  - **Meta-apparna (WhatsApp, Messenger, Instagram):** efter ”Anslut” visas Callback-URL och
    Verifieringstoken — klistra in dem i Meta-appens webhookinställningar och prenumerera på
    `messages` (Messenger/Instagram även `messaging_postbacks`). Statusen blir ”Ansluten” när Meta
    har verifierat. I utvecklingsläge svarar boten bara personer med roll i appen; för att svara
    alla kunder måste appen vara publicerad (Live) med meddelandebehörigheten godkänd i **App
    Review** (Messenger: `pages_messaging`; Instagram: `instagram_business_manage_messages` med
    Instagram-inloggning eller `instagram_manage_messages` via Facebook-sida).
  - **WhatsApp:** permanent systemanvändartoken med `whatsapp_business_messaging` +
    `whatsapp_business_management`. Kommer inga meddelanden fram trots verifierad webhook:
    prenumerera appen på WhatsApp Business-kontot (WABA) med `POST /<WABA-ID>/subscribed_apps` i
    Graph API med samma token.
- [ ] **Zendesk: rekommendera OAuth-klient.** Admin Center → Appar och integrationer → API:er →
  OAuth-klienter, typ Konfidentiell (tillåt `tickets:write users:read users:write` om scopes
  begränsas); ärendena skapas i namnet på administratören som skapade klienten. API-token finns
  bara kvar för äldre konton: konton skapade från 28 juli 2026 kan inte använda API-tokens, en
  token som inte använts på 30 dagar stängs av automatiskt (boten använder den bara när en händelse
  skickas), Zendesk slutar skapa nya 27 oktober 2026 och alla tokens slutar fungera 30 april 2027.
  Be kunder som kopplat med token att byta före dess.
- [ ] **Juridik: låt jurist granska de nya integrationsstyckena** i `/integritetspolicy` (avsnittet
  ”Integrationer som du själv kopplar”, att kanalens avsändar-id och visningsnamn sparas, att
  integrationsnycklar lagras krypterade) och i `/villkor` (tjänstebeskrivningen med
  integrationerna). Särskilt: roller (kunden personuppgiftsansvarig, vi biträde) och
  överföring till tjänster utanför EU som kunden själv kopplar (Meta, Telegram, Slack, Discord,
  Zendesk, Freshdesk, LiveChat, Zapier, Shopify).

### Vercel / miljö
- [ ] `NEXT_PUBLIC_DOMAIN` = produktionsorigin (success/cancel/return-URL:er) och `STRIPE_*` =
  LIVE-nycklar/price-id:n före lansering.
- [ ] **Kör `scripts/setup-secrets.ps1`** (2026-10-09): lägger in `CHAT_TOKEN_SECRET` och
  `CRON_SECRET` (slumpade, hemliga — utan `CRON_SECRET` svarar båda cron-jobben 503) och
  `PUBLIC_APP_URL` i Vercel (Production), plus `NEXT_PUBLIC_CONTACT_EMAIL` / `ALERT_EMAIL` med
  `-ContactEmail` / `-AlertEmail`. Befintliga nycklar byts bara med `-Rotate`. Redeploy efteråt.
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-secrets.ps1 -ContactEmail <adress> -AlertEmail <adress>`
- [ ] `NEXT_PUBLIC_CONTACT_EMAIL` aktiverar "Kontakt"-kolumnen i sidfoten och fyller kontaktraden på
  juridiksidorna (tills dess visas en gul platshållare) — sätts av skriptet ovan.
- [ ] `RESEND_API_KEY` + `EMAIL_FROM` (verifierad avsändardomän i Resend): utan dem skickas inga
  mejl alls (leadnotiser, larm, flyttinbjudningar).
- [ ] När AI-leverantören byts (t.ex. `NEXT_PUBLIC_AI_PROVIDER=vertex`): sätt även
  `LEGAL_UPDATED=<dagens datum>` — integritetspolicyn och villkoren ändras med leverantören — och
  mejla befintliga betalande kunder om bytet innan det gäller (villkoren §12).
- [ ] Efter nästa deploy körs serverfunktionerna i Dublin (`vercel.json` `"regions": ["dub1"]`):
  kontrollera att svaren har `X-Vercel-Id: …::dub1::…`.
- [ ] Lägg till en git-remote (GitHub) — repot har ingen idag, så inget kan pushas.

### Stripe Dashboard (TEST och LIVE)
- [ ] Product catalog: döp om produkterna till **Starter** (`STRIPE_PRICE_STARTER`, idag
  "Nybörjare"), **Growth** (idag "Pro") och **Pro** (idag "Max pro") så Checkout/kvitton
  matchar appen.
- [ ] Settings → Business details: publikt företagsnamn "ChatBot AI" (Checkout visar idag
  kontoinnehavarens personnamn).
- [ ] Settings → Billing → Customer portal: aktivera, slå på "Cancel subscriptions", "Update
  payment methods" och "Invoice history", spara (krävs i LIVE; test gav redan portal-URL).
- [ ] Developers → Webhooks → endpointen: lägg till eventen `checkout.session.async_payment_succeeded`,
  `checkout.session.async_payment_failed` och `customer.subscription.created` utöver befintliga
  (completed/updated/deleted/invoice.payment_failed).
- [ ] **Öppna riktiga betalningar — i den här ordningen:** företag → momsregistrering → Stripe i
  live-läge (`STRIPE_SECRET_KEY=sk_live_…`, live-priserna `STRIPE_PRICE_STARTER/GROWTH/PRO`,
  live-endpointens `STRIPE_WEBHOOK_SECRET`) + Stripe Tax (nästa punkt) → `STRIPE_AUTOMATIC_TAX=true`
  → redeploy. Med live-nyckeln öppnar köpen av sig själva. Till dess: låt testnyckeln stå kvar i
  Vercel (köpen är automatiskt stängda i produktion) och sätt **inte** `STRIPE_ALLOW_TEST_MODE` där
  (eller bara för en egen kort test — ta bort den direkt efter). Kontrollera i Admin → ”Betalningar (Stripe)”.
- [ ] **Stripe Tax — innan första riktiga betalningen.** Villkoren och prissidan säger "exkl. moms,
  moms tillkommer", men utan Stripe Tax läggs ingen moms på. Koden är klar (2026-10-09): aktivera
  Stripe Tax, sätt de tre prisernas tax behaviour till "exclusive", momsregistrera företaget och
  sätt sedan `STRIPE_AUTOMATIC_TAX=true` i Vercel + redeploy (Checkout lägger då på moms, tar in
  momsregistreringsnummer och kräver faktureringsadress). Inte tidigare — Stripe avvisar Checkout
  med automatic_tax innan Stripe Tax är aktiverat.
- [ ] **Klarna** (valfritt): aktivera under Settings → Payment methods, lägg till
  `params['payment_method_types[1]'] = 'klarna'` i `checkout/route.js` och återinför badgen i
  `PricingPage.jsx`. Webhooken kräver redan `payment_status === 'paid'`, så fördröjda metoder är säkra.
- [ ] Notera: checkout-rate-limit är 5/min per IP i minnet — upprepade uppgraderingstester från
  samma maskin kan ge 429 i upp till 60 s.

### Supabase
- [ ] Authentication → Password policy: sätt server-side minimilängd till **8** så den matchar
  klientpolicyn i `src/lib/passwordPolicy.js` (GoTrue-default är 6).
- [ ] Valfritt: slå på leaked-password protection (HaveIBeenPwned) på samma skärm.
- [ ] **Godkänn och kör `supabase/migrations/20261009120000_advisor_hardening.sql`** (Supabase-
  advisorernas varningar: triggerfunktioner gick att anropa via API:t, två funktioner utan fast
  `search_path`, RLS-policyer med `auth.uid()` per rad, två FK-index). Ändrar inga data; prövad i
  en lokal Postgres (scratchpad/launch/fixtests/schema-pglite.test.mjs).
- [ ] `profiles.is_admin` är `false` för alla konton (2026-10-09). Admin-undantagen i databasen
  (bot-taket) och i `src/lib/ownerPlan.js` (trial-utgången) gäller bara med flaggan — sätt den för
  adminkontot (`scripts/seed-admin.mjs` gör det, med service-rollen). Adminpanelen syns ändå via
  `ADMIN_EMAIL`.
- [ ] `integration_interests` används numera bara för historiken i Admin (”Meddela mig” finns inte
  kvar, inga nya rader). Om tabellen inte är applicerad live rapporterar `/api/health/schema`
  `tables.integration_interests:false` — kör `supabase/schema.sql` (idempotent). Integrationerna
  själva kräver ingen schemaändring (de ligger i `bots.config`, ADR-012).
- [ ] Rensa gamla sidodumpar i ett svep (annars sker det när ägaren loggar in nästa gång):
  `update public.bots set knowledge = (knowledge - '_scrapedPages') || jsonb_build_object('_raw', left(knowledge->>'_raw', 8000)) where knowledge ? '_scrapedPages' or length(knowledge->>'_raw') > 8000;`

### Konton och demo
- [ ] **Byt lösenordet på adminkontot och testkontona (CH-03/CH-07).** Seed-skripten hade svaga,
  bokstavliga lösenord (borttagna ur filerna 2026-10-09, men kvar i git-historiken). Har
  `scripts/seed-admin.mjs` någon gång körts mot produktionen har adminkontot det gamla lösenordet:
  byt det nu (”Glömt lösenord”, eller `node scripts/seed-admin.mjs --i-know-this-is-production
  --reset-password` — det nya slumpas och visas en gång). Testkontona `supatest@example.se` och
  `anna@example.se` i produktionsdatabasen: radera dem eller kör `seed-test-user.mjs` /
  `seed-user2.mjs` med samma två flaggor.
- [ ] **TRIAL-UTGÅNGEN ÄR LIVE:** alla befintliga konton är trials äldre än 14 dagar, så
  Autolane-demoboten (ägare = gmail-kontot, 57 d) och "DB Test Bot" (81 d) svarar med
  "begränsad"-repliken vid deploy. Ge Autolane-kontot en betald plan (Stripe test-checkout,
  eller `subscriptions.plan='pro', status='active'` med service-rollen), flytta demoboten
  till adminkontot (`jonatan@andersaman.se`, undantaget från utgång) eller lägg dess bot-id i
  `DEMO_BOT_IDS` i Vercel (finns redan i `.env.local`; undantar bara från utgången, inte från taken).
- [ ] **Scanna om Autolane-demoboten** (och ev. kundbots) så kunskapsbasen får /kontakt/ +
  öppettider, rena modellnamn, kategorier och status. Lagrad kunskap migreras inte.
- [ ] Health-checks är admin-only: öppna `/api/health/schema` och `/api/health/supabase` inloggad
  som adminkontot (anonyma anrop ger 403 by design).

### Verifiering efter deploy
- [ ] Kör en riktig widgetchatt på ett icke-utgånget konto: `usage` +1/+1, en rad i
  `conversations`, Dashboard "Konversationer" = 1, Arkiv visar transkriptet märkt Widget.
- [ ] Träning → lägg till ett par → ställ samma fråga i widgeten (den publika chatten läser
  `bots.config.training`).
- [ ] Bevaka loggen för `[scan] … nådde max_tokens` — syns det på analyze-passet även efter att
  taket i `anthropic.js` höjts till 8192, sänk `ANALYZE_CONTEXT_CHARS` i `src/lib/ai.js`.
- [ ] Meddela ev. befintliga webhook-/Zapier-mottagare att `X-ChatBotAI-Signature` nu är
  `t=<unix>,v1=<hex>` (HMAC-SHA256 över `t + "." + råkropp`) i stället för råhemligheten.
- [ ] Integrationer (Growth/Pro-konto, på den publika adressen): anslut Telegram och skriv till
  boten → svar i Telegram, samtalet i Arkiv märkt Telegram, `usage` +1. Koppla Slack eller Discord
  och lämna en lead i widgeten → notis, och kortet visar senaste händelse. Anslut + synka en
  Shopify-/WooCommerce-butik → produkterna i botens kunskap, priser i butikens valuta. Anslut
  LiveChat → knappen ”Prata med en människa” syns i widgeten inom ~5 minuter (`/api/bot` cachas).

### Juridik / texter
- [ ] Fyll i platshållarna på /integritetspolicy och /villkor: företagsnamn, org.nr, adress,
  tingsrätt, lagringstid för chattar/leads, länk till biträdesavtal (DPA). Låt jurist granska
  och ta sedan bort "Utkast"-bannern.
- [ ] Verifiera överföringsmekanism per USA-leverantör (Anthropic, Stripe, Vercel: SCC och/eller
  EU-US DPF) innan policyn publiceras.
- [ ] Vill du ha Kontakt-/Om oss-sidor: skapa dem och lägg tillbaka sidfotslänkarna (togs bort
  i stället för att lämnas döda).
- [ ] Träningspar som låg i en gammal webbläsare migreras automatiskt första gången ägaren öppnar
  Träning för den boten i den webbläsaren — inget att göra server-side.
