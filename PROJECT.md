# ChatBot AI — Projektbeskrivning

## Vision
En SaaS där **företag kan köpa AI-chatbots** som tränas på företagets egen hemsida och
sedan svarar deras kunder dygnet runt. Riktad mot den svenska marknaden (svenskt UI,
priser i kr/mån exkl. moms, kortbetalning via Stripe — Klarna när det aktiverats i Stripe).
En kund anger sin hemsida → plattformen scannar sajten → en bot byggs som expert på just
det företaget → kunden klistrar in en rad kod på sin sajt och boten är live.

## Affärsmodell
Prenumeration (månadsvis, exkl. moms) i tre betalda nivåer + trial. Definieras i
`src/lib/constants.js` (`PLANS`); Stripe-priser via `STRIPE_PRICE_*`.

| Plan | Pris/mån | Bots | Konv/mån | Growth-integrationer* |
|------|----------|------|----------|----------------|
| Trial | 0 kr (14 dgr från `profiles.created_at`) | 1 | 100 | – |
| Starter | 699 kr | 2 | 1 000 | – |
| Growth | 1 599 kr | 5 | 5 000 | ✓ |
| Pro | 4 699 kr | 15 | 25 000 | ✓ |

- \* Kanaler (Telegram, WhatsApp, Messenger, Instagram), Slack, Discord, Zendesk, Freshdesk,
  LiveChat, webhook och Zapier. Hemsida, WordPress, Shopify och WooCommerce ingår i alla planer.
- Bot-taket enforce:as i databasen (trigger `bots_enforce_limit`), konversationstaket och
  trial-utgången i `/api/chat/[id]` och kanalerna (gemensam policy i `src/lib/ownerPlan.js`).
  Vid taket svarar boten en vänlig "begränsad"-replik.
- Planen gäller när `subscriptions.status ∈ {active, trialing, past_due}`, annars trial.
- När konversationstaket nås pausas nya samtal till nästa månad eller uppgradering
  (ingen överkonsumtionsavgift).
- Admin/ägarkonto: `profiles.is_admin = true` (fallback `ADMIN_EMAIL`, bara server-side i `src/lib/adminEmail.js`; appen frågar `GET /api/admin/me`),
  undantaget från trial-utgång så demoboten på egna sajten fortsätter svara (botar i
  `DEMO_BOT_IDS` likaså). Undantaget gäller bara utgången: Growth-integrationerna följer
  prenumerationen, så även adminkontot behöver Growth/Pro för att testa dem.

## Stack (faktisk)
- **Next.js 14** (App Router) + **React 18** i ren **JSX** — ingen TypeScript (ADR-001).
- **Inline-styles + `src/styles/globals.css`** (CSS-variabler, `.dark`) — Tailwind inaktivt (ADR-002).
- **Supabase** — Postgres är källan till sanning (profiles, bots, subscriptions, leads, usage,
  conversations, processed_webhook_events, integration_interests — den sista bara historik),
  **Supabase Auth** (e-post/lösenord, e-postbekräftelse, glömt lösenord) och RLS på alla tabeller.
  Region eu-west-1 (Irland). Integrationernas tillstånd ligger i `bots.config.integrations`
  (ingen egen tabell — ADR-012). Lokalt och produktion delar samma databas.
- **Anthropic Claude API** — `claude-fable-5` (`SCAN_MODEL`) för djup hemsidescanning,
  `claude-sonnet-4-6` (`CHAT_MODEL`) för livechatt med streaming och prompt-cache.
  Webbsökning i chatten är **av** (`CHAT_WEB_SEARCH=false`) efter mätning (ADR-011).
  Anthropic (USA) är AI-leverantör som standard; nyckeln finns bara server-side. En enda
  variabel, `NEXT_PUBLIC_AI_PROVIDER=openai` (eller `=gemini`: Google Gemini på gratisnivån,
  bara för test; eller `=vertex`: Gemini på Google Cloud Vertex AI med tjänstekonto, betalt via
  Google Clouds provperiod, plats `GCP_LOCATION`, standard `eu`), byter leverantör — både anropen och texterna i
  integritetspolicy, villkor och landningssida (`src/lib/aiProviderInfo.js`, se README →
  ”Byta AI-leverantör”). Utan AI-kredit på kontot svarar alla botar (widget, delningslänk,
  kanaler) ärligt att chatten är tillfälligt ur funktion, med företagets kontaktuppgifter
  (`friendlyOutage` i `ownerPlan.js`) — det syns som varning på Dashboard och som AI-status i
  Admin (`bots.config.aiStatus`). Kanalernas integrationskort blir inte röda av det
  (`lastErrorScope: "platform"`, felet ligger inte i kopplingen).
- **Stripe** via REST direkt (ingen SDK) — Checkout, planbyte med proration, Billing Portal,
  signaturverifierad + idempotent webhook. Kortdata hanteras av Stripe. Stripe Tax ej aktiverat.
- **Vercel** — hosting (functions i arn1/Stockholm). OBS: Deployment Protection måste vara av
  (widget, delningslänk, kanalernas webhooks och Stripe-webhooken är anonyma anrop). Arbete efter
  svaret (AI-svar i kanaler, notiser) hålls vid liv med `waitUntil` (`@vercel/functions`).
- **Widget** — `public/widget.js` serveras från appens egen origin; embed-koden byggs från
  `window.location.origin` (ingen extern CDN). Visar ”Prata med en människa” när LiveChat är kopplad.

## Kärnflöde
1. **Konto** — registrering via Supabase Auth (trigger skapar profil + trial-prenumeration).
2. **Skapa bot** — väljer mall, anger sin hemsida (DB-triggern stoppar över planens bot-tak).
3. **Scanning** — `scanWebsite()` (`src/lib/ai.js`) kartlägger sajten via `/api/crawl`
   (sitemap, meny, listsidor, paginering, JSON-LD, Jina Reader för JS-renderade sidor,
   info-sidor som kontakt/öppettider/FAQ prioriterade) och bygger en kunskapsbas via
   streamade analyspass (`/api/ai`). Sparas i `bots.knowledge` (utan sidodumpar).
4. **Anpassa** — namn, färg, avatar, position, välkomstmeddelande, snabbsvar (max 6) i BotBuilder.
5. **Träna** — egna fråga/svar-par i `bots.config.training` (`TrainingPage`), lästa av den publika chatten.
6. **Publicera** — embed-kod (`EmbedPage`), delningslänk `/chat?bot=<id>` och de 15 integrationerna
   i `IntegrationsPage` (katalog `src/lib/integrations/catalog.js`, server `/api/integrations`).
7. **Chatta** — widget/delningslänk → `/api/chat/[id]` (SSE). Servern utfärdar en signerad
   samtals-token så att uppföljningsmeddelanden räknas som samma samtal; räknar i `usage`
   (atomisk RPC) och sparar transkriptet i `conversations`. Telegram/WhatsApp/Messenger/Instagram
   → `/api/channels/<provider>/<botId>` → `botEngine.js` (samma prompt, modell och tak; tråd per
   avsändare i `conversations`, källa = kanalen).
8. **Händelser till ägarens system** — ny lead (`/api/lead`) och nytt samtal skickas via
   `dispatch.js` till webhook, Zapier, Slack, Discord, Zendesk och Freshdesk (Growth/Pro).
9. **Följa upp** — Arkiv (samtal, märkta med källa), Analys (usage + conversations), Leads
   (kontaktuppgifter). Anonyma besökare spåras inte.

## Integrationer (arkitektur i korthet)
Detaljer i README (”Integrationer — arkitektur”), lagringsbeslutet i ADR-012.
- **Katalog → API → providers:** `src/lib/integrations/catalog.js` (15 integrationer, 6 kategorier,
  plan `all`/`growth`, fält, steg, actions) styr både `IntegrationsPage` och servern.
  `/api/integrations` (GET status, POST connect/test/verify/sync/disconnect; inloggad ägare,
  same-origin, planen kontrolleras på servern) anropar `providers/<id>.js`.
- **Tillstånd:** `bots.config.integrations[<id>]` via `store.js` (compare-and-swap på
  `bots.updated_at`). Hemligheter AES-256-GCM-krypterade med nyckelring
  (`INTEGRATIONS_ENC_KEY` → Supabase-nyckeln); äldre värden krypteras om när de används/sparas.
  Webbläsaren ser bara ledtrådar; `botStore.js` skriver aldrig integrationsnycklarna.
- **In:** `/api/channels/<provider>/<botId>` — verifierar (Telegram secret_token, Metas HMAC +
  verify-token), deduplicerar i `processed_webhook_events`, svarar 200 direkt och låter
  `botEngine.js` svara i bakgrunden. Callback-URL:en kräver en publik https-adress (`PUBLIC_APP_URL`).
- **Ut:** `dispatchEvent()` — `lead.created` och `conversation.started` till alla anslutna
  webhook/Zapier och de notis-/ärendekopplingar som valt händelsen; ≤ ~5 s, efter svaret, utfallet
  sparas som `lastEventAt`/`lastError`.
- **Produktsynk:** Shopify/WooCommerce → upp till 500 produkter i `bots.knowledge.items`
  (`source` = butiken), bara i butikens egen valuta; en omscanning behåller dem, frånkoppling tar bort dem.
- **Överlämning:** LiveChat — `/api/bot` exponerar bara licensnummer + knapptext (`handover`) och
  widgeten öppnar LiveChat på sidan.
- **AI-hälsa:** `aiHealth.js` → `bots.config.aiStatus` (Dashboard-varning, Admin AI-status,
  kanalens ”Senaste fel”).

## Komponentkarta (nuvarande)
```
public/widget.js            Embed-widgeten (config från /api/bot, chatt via /api/chat SSE, leads via /api/lead,
                            tumme upp/ner via /api/chat/<id>/feedback; 8 språk)
vercel.json                 Cron: /api/cron/rescan 03:00 UTC, /api/demo/cleanup 04:30 UTC (kräver CRON_SECRET)
supabase/schema.sql         Schema + RLS + triggers + RPC (idempotent)
src/
  middleware.js             Inloggningsgrind utan nätverksanrop (auth-cookie finns?): / ↔ /app, /login ↔ /app,
                            /app/* → /login?next=; matcher bara /, /login, /signup, /app/*
  app/
    page.jsx                Server-renderad landningssida (SEO) + LandingClient.jsx (CTA:er, e-postlänkar)
    app/                    Appen: layout.jsx monterar components/AppShell.jsx (global state, en URL per sida
                            enligt lib/routes.js); [[...slug]]/page.jsx ger 404 för okända /app-sökvägar
    login/, signup/         Server-renderade inloggnings-/registreringssidor (AuthPage, ?next=, ?notice=)
    robots.js, sitemap.js   SEO (bas-URL från PUBLIC_APP_URL / NEXT_PUBLIC_DOMAIN)
    layout.jsx              Root layout
    not-found.jsx           404
    chat/page.jsx           Publik chatt-yta (delningslänk)
    checkout/page.jsx       Stripe-retur (litar bara på /api/checkout/verify)
    reset-password/page.jsx Lösenordsåterställning
    integritetspolicy/, villkor/   Juridiska sidor (UTKAST — jurist ska granska)
    api/
      ai/route.js           Proxy mot AI-leverantören för scanning (Origin-gate, rate-limit, SSE, 8192 tokens)
      crawl/route.js        HTTP-skal (Origin-gate, rate-limits) runt lib/crawler.js
      bot/[id]/route.js     Publik bot-config (allowlist, ingen kunskapsbas/webhook-hemlighet, cache 5 min)
      chat/[id]/route.js    Publik chatt: samtals-token, plan-/trial-/samtalstak, träningsdata,
                            increment_usage, conversations, conversation.started till integrationerna,
                            AI-utfall → bots.config.aiStatus
      chat/[id]/feedback/   Besökarens tumme upp/ner (samtals-token, rate-limits) → message_feedback
      lead/route.js         Leads via lib/leads.js (+ lead.created och lead-mejl till ägaren)
      cron/rescan/          Veckovis automatisk omskanning (Vercel Cron, CRON_SECRET) → lib/scanServer.js
      demo/scan, demo/chat  Landningssidans demo "Testa på din egen webbplats" (lib/demo.js)
      demo/cleanup/         Raderar gamla demosessioner (Vercel Cron, CRON_SECRET)
      waitlist/             Väntelista från landningssidan (service role)
      checkout/route.js     Stripe Checkout / planbyte (inloggad, sameOrigin, rate-limit)
      checkout/verify/      Verifierar sessionen mot Stripe (payment_status === paid)
      portal/route.js       Stripe Billing Portal
      webhook/route.js      Stripe-events: signatur (fail-closed) + idempotens
      integrations/route.js Ägarens integrationer: GET status, POST connect/test/verify/sync/disconnect
      channels/[provider]/[botId]/route.js  Inkommande Telegram/WhatsApp/Messenger/Instagram: verifierar,
                            svarar 200 direkt, AI-svaret i bakgrunden (lib/background.js)
      admin/stats/route.js  Adminpanel (403 för icke-admin)
      admin/waitlist/       Väntelista + demoanvändning för Admin (403 för icke-admin)
      health/*              Schema-/DB-hälsa (admin-only, rate-limitad)
  components/               Alla sidvyer (Dashboard, BotBuilder, Training, Embed, Integrations,
                            Visitors=Leads, Archives, Analytics, Pricing, Billing, Settings, Admin, Auth, Landing)
    integrations/           Integrationssidans delar (översikt, kort, detaljsida, formulär, statuspanel)
  lib/
    ai.js                   scanWebsite() (= runScan med webbläsarens beroenden) + liveChat()
    crawler.js              Djup crawler (sitemap, paginering, JSON-LD, Jina, robots.txt) — server only;
                            delas av /api/crawl, omskanningen och demon
    scanServer.js           Server-sidans omskanning (runScan + crawler i processen, beslut: behåll gammal
                            kunskap om den nya är sämre); autoRescan.js = reglerna/texterna (klient-säker)
    routes.js               Sidnyckel ↔ URL (/app/...), ?next=-validering, middleware-beslut
    leads.js, contactCapture.js   Leads (formulär + e-post/telefon som besökaren skriver i chatten)
    notify.js, email.js     Lead-mejl till ägaren + AI-larm till plattformsägaren (Resend)
    noAnswer.js, trainingInsights.js, feedbackStore.js   "Kunde inte svara", tumme ner → Träning/Översikt
    demo.js                 Landningsdemons skanning, kvoter och städning (server only)
    chatPrompt.js           Systemprompt (KRITISK REGEL — LÄSES FÖRST, retrieval, prisfilter)
    anthropic.js            Server-side Anthropic (call/stream); lämnar över till openaiChat.js vid OpenAI
    aiProviderInfo.js       Vilken AI-leverantör som gäller (NEXT_PUBLIC_AI_PROVIDER) — server och klient
    constants.js            PLANS, PLAN_FEATURES, SCAN_MODEL/CHAT_MODEL, CHAT_WEB_SEARCH (klientsäkert)
    adminEmail.js           ADMIN_EMAIL — bara server-side (aldrig i webbläsarens JavaScript)
    botStore/leadStore/profileStore/conversationStore.js   Supabase-datalager (RLS)
    integrations/           catalog.js (15 integrationer, delas av klient och server), store.js
                            (bots.config.integrations, compare-and-swap), crypto.js (nyckelring,
                            enc:v2), dispatch.js, http.js (safeFetch), providers/<id>.js
    integrationsClient.js   Integrationssidans anrop mot /api/integrations
    requestUser.js          Inloggad användare i API-routes (Bearer-token eller cookie-session)
    botEngine.js            Kanalernas svarsmotor (samma prompt/regler som /api/chat)
    ownerPlan.js, transcript.js   Ägarens plan/tak + samtalslagring (delas av chatt och kanaler)
    aiHealth.js             bots.config.aiStatus (Dashboard-varning + Admin AI-status)
    background.js           runInBackground() → Vercel waitUntil
    supabase/{client,server,admin}.js
    convToken.js            Signerad samtals-token (HMAC-SHA256, 24 h, botbunden)
    apiGuard.js             sameOriginOk + in-memory rate-limit
    ssrf.js                 assertSafeUrl (värdebaserad IPv4/IPv6-kontroll, DNS-upplösning) +
                            guardedFetch (samma kontroll när anslutningen öppnas)
    webhook.js              Utgående webhooks, X-ChatBotAI-Signature (t=…,v1=…)
    stripe-config.js        STRIPE_PRICES från env + REST-hjälpare (server-only)
    stripeWebhook.js        verifyStripeSignature()
    subscriptions.js        applyStripeEvent() → subscriptions (UPSERT)
    adminAuth.js            getAdminContext() från sessionen
    passwordPolicy.js       Lösenordsregler (min 8 + blocklista)
    storage.js              Kvarvarande localStorage: offline-cache per användare + byggarens testchattar
  styles/globals.css        CSS-variabler (ljust default + .dark), micro-interactions
```

## Säkerhetsstatus (2026-09-30)
- **RLS** på alla tabeller; trigger `profiles_protect_columns` hindrar inloggade från att ändra
  `is_admin`/`email`/`id`/`created_at`. `subscriptions`, `usage`, `conversations`,
  `processed_webhook_events` skrivs bara av servern (service-rollen).
- **Stripe-webhook** signaturverifierad (HMAC-SHA256, replay-fönster, fail-closed utan secret),
  idempotent per event-id, plan endast vid `payment_status === "paid"`.
- **SSRF-guard** (`ssrf.js`) på crawl, integrationer och utgående webhooks — även när anslutningen
  öppnas (`guardedFetch`, skydd mot DNS-rebinding): privata/loopback/link-local nät,
  IPv4-mappade/NAT64/6to4-adresser, numeriska värdar och interna suffix blockeras.
- **Admin** avgörs server-side (`profiles.is_admin` via service-rollen); adminpanel, stats och
  health-routes svarar 403 annars.
- **Publika endpoints** rate-limitade per IP och per bot; `/api/bot` läcker inte kunskapsbas eller
  webhook-hemligheter; klientens offline-cache är per användare och rensas vid utloggning.
- **Integrationer:** hemligheter krypterade (AES-GCM, `INTEGRATIONS_ENC_KEY` — samma värde i alla
  miljöer), bara ledtrådar (”…AbC1”) till webbläsaren; inkommande kanalmeddelanden verifieras
  (Telegrams secret_token, Metas HMAC), dedupliceras och rate-limitas per IP, bot och avsändare.
  Planen kontrolleras på servern vid varje leverans, kanalsvar och LiveChat-knapp.
- **Öppet:** rate-limit-store i minnet (nollställs vid cold start); ingen per-användar-tokenkvot;
  `/api/crawl` och `/api/ai` skyddas av Origin-gate + rate-limit, inte av inloggning; RLS
  (`bots_update_own`) låter ägaren tekniskt skriva sin egen `bots.config.integrations` direkt mot
  Supabase — appen gör det aldrig, och servern validerar värdar/SSRF och plan igen vid användning
  (ADR-012).

## Status
Produkten är **tekniskt körbar för första betalande kund**: databas, auth, widget,
entitlement Stripe↔plan, signerad webhook och plan-tak är implementerade och verifierade
(E2E-kampanj 2026-09-02, se ADR-011). Sedan 2026-09-30 är alla 15 integrationer byggda — inga
”kommer snart” kvar (ADR-012); kanalerna kan tas i drift först på den publika https-domänen.
**Läge 2026-09-30: ingen bot svarar med AI** — Anthropic-kontot saknar kredit, så varje fråga
får ett vänligt felmeddelande tills kontot fylls på. Det som återstår före lansering är i
huvudsak **manuella steg** (AI-kredit, Vercel Deployment Protection av, `PUBLIC_APP_URL` och
`INTEGRATIONS_ENC_KEY`, Stripe-produktnamn, kundportal i live-läge, Stripe Tax, övriga
miljövariabler), **juridisk granskning** av utkasten till integritetspolicy och villkor (inkl.
de nya integrationsstyckena), samt per-användar-tokenkvot med delad rate-limit-store. Se `TASKS.md`.
