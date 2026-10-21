# DECISIONS — Tekniska beslut (ADR-logg)

Format: kort beslut, kontext, konsekvens. Senaste först. Markerar var nuläget avviker
från målstacken (Next.js + TypeScript + Tailwind + Supabase + Stripe + Vercel).

---

## ADR-012 — Integrationernas tillstånd i `bots.config`, krypterade hemligheter, CAS-skrivningar (2026-09-30)
**Kontext:** Integrationssidan byggdes om så att alla 15 integrationer i
`src/lib/integrations/catalog.js` fungerar (tidigare 4 live, 11 ”kommer snart”). Varje koppling
behöver tillstånd per bot och integration: inställningar, hemligheter (bot-tokens, Meta-tokens,
API-nycklar, webhook-URL:er som i sig är nycklar), status, senaste fel/händelse och visningsinfo.
Sessionen som byggde det hade **ingen DDL-åtkomst** — inga nya tabeller, kolumner eller
RLS-policyer kunde skapas. Befintligt schema fick räcka: `bots.config` (jsonb),
`conversations` och `processed_webhook_events`.
**Beslut:**
1. **Tillståndet ligger i `bots.config.integrations[<id>]`** = `{ enabled, status
   ("connected"|"pending"|"error"), settings, secrets, secretHints, info, message, lastError,
   lastErrorAt, lastEventAt, connectedAt, updatedAt }`. Den äldre webhooken behåller
   `config.webhookUrl`/`webhookSecret` (befintliga kunders kopplingar ligger där); `store.js`
   döljer skillnaden (`readState`/`saveState`/`patchState`/`recordResults`/`connectedIds`), och
   `webhookSecret` krypteras vid nästa skrivning. Kanalernas samtal ligger i `conversations`
   (nyckel `<provider>:<botId>:<avsändare>:<tid>`, `source` = kanalen) och dedupe av plattformarnas
   omleveranser i `processed_webhook_events` (id `<provider>:<botId>:<meddelande-id>`, rensas efter
   8 dagar; Stripes rader rörs inte).
2. **Hemligheterna krypteras** eftersom ägaren kan läsa hela `bots`-raden via RLS (även
   `config.integrations`): alla hemliga fält som EN AES-256-GCM-krypterad JSON,
   `enc:v2:<nyckel-id>:<base64url(iv|tag|chiffertext)>` (`crypto.js`). Nyckelring:
   `INTEGRATIONS_ENC_KEY` → `SUPABASE_SECRET_KEY` → `SUPABASE_SERVICE_ROLE_KEY` — den första som är
   satt krypterar, alla som är satta får dekryptera (`enc:v1:` utan nyckel-id provas mot alla).
   Varje skrivning som rör en koppling krypterar om dess hemligheter under aktuell nyckel, så en
   rotation = sätt den nya nyckeln och låt den gamla ligga kvar tills inget gammalt finns kvar.
   Ett värde ingen nyckel kan öppna förstörs aldrig; kopplingen visas som ”anslut igen”.
   Webbläsaren får bara `secretHints` (”…AbC1”); `/api/bot` exponerar bara LiveChat-licensen och
   knapptexten (`handover`).
3. **Server-ägda nycklar:** `SERVER_OWNED_CONFIG_KEYS` = `integrations`, `webhookUrl`,
   `webhookSecret` (i den klientsäkra katalogen). `botStore.js` tar bort dem ur appens bot-objekt
   (aldrig i React-state eller localStorage) och skriver dem aldrig; `aiStatus` är läsbar men
   skrivs också bara av servern. Så kan en gammal flik i byggaren inte återuppliva en frånkopplad
   koppling.
4. **Compare-and-swap på `bots.updated_at`** (trigger `bots_touch_updated_at`) för varje
   skrivning: `store.mutateConfig` läser `config` + `updated_at`, ändrar en kopia och skriver bara
   om `updated_at` är oförändrad — annars läses raden om (upp till 12 försök med slumpad
   exponentiell paus). Byggarens sparningar (`botStore.js`, 8 försök) och produktsynken
   (`_products.writeSyncedItems`, som i samma radversion kontrollerar att butikskopplingen finns
   kvar) gör samma sak. Skrivtrycket hålls nere: dispatch sparar alla utfall i EN skrivning,
   kanalernas status skrivs högst en gång per minut och bot+kanal, `aiStatus` bara vid växling
   ok ↔ fel (högst var 5:e minut under ett avbrott).
**Varför inte egen tabell nu:** ingen DDL-åtkomst; ingen migrering behövs vid deploy (bara kod);
tillståndet följer boten (RLS-ägarskapet gäller redan, raderad bot = borta kopplingar); kanalrouten,
dispatch och `/api/bot` läser ändå bot-raden — ingen extra fråga på widgetens/leadens väg.
**Avvägningar (kända nackdelar):**
- **En het rad.** Varje statusskrivning skriver om hela `config` och tävlar med byggarens
  sparningar, dispatch, kanaler och `aiStatus` om samma rad. CAS gör det korrekt men inte gratis;
  efter 12 förlorade försök misslyckas skrivningen (”Kunde inte spara (för många samtidiga
  ändringar)”).
- **Ägaren kan tekniskt skriva sin egen `config.integrations`** direkt mot Supabase (RLS
  `bots_update_own` gäller hela raden). Appen gör det aldrig, och servern litar inte på det:
  planen kontrolleras vid varje leverans/kanalsvar/LiveChat-knapp, Slack/Discord-URL:er och
  Zendesk/Freshdesk-domäner valideras igen vid varje sändning, användarangivna adresser går via
  SSRF-skyddet, och krypterade hemligheter kan inte förfalskas utan nyckeln. Det påverkar bara
  ägarens egna botar.
- **Chiffertexten syns för ägaren** (oanvändbar utan nyckeln) och **nyckelhanteringen är kritisk:**
  lokalt och produktion delar databas, så `INTEGRATIONS_ENC_KEY` (eller Supabase-nyckeln) måste
  vara samma i båda — annars ”anslut igen” på ena sidan och avvisade kanalmeddelanden (401).
- **Inga frågor över botar** (t.ex. ”alla Telegram-kopplingar”, schemalagd synk, påminnelser om
  Zendesks API-token), inga constraints/index, ingen historik — bara senaste fel och händelse.
- **Inkommande anrop hittar boten via bot-id i URL:en**, så en Meta-app betjänar en bot per kanal;
  routning på `phone_number_id`/sid-id skulle kräva ett index.
**När vi ska flytta till en egen tabell** (t.ex. `bot_integrations (bot_id → bots on delete
cascade, provider, enabled, status, settings jsonb, secrets text, secret_hints jsonb, info jsonb,
last_error, last_error_at, last_event_at, connected_at, updated_at, unique(bot_id, provider))`,
RLS: ägaren läser, bara servern skriver): när DDL-åtkomst finns och helst före större kundvolym,
och senast när något av detta inträffar — CAS-misslyckanden/”för många samtidiga ändringar” i
loggen eller krockar med byggarens sparningar; behov av frågor över alla botar (admin-översikt,
cron-jobb); en leveranslogg/omförsökskö; en delad Meta-app med routning per nummer/sida; eller
krav på att ägaren inte ska kunna skriva kopplingarna själv.
**Konsekvens / migreringsväg:** `store.js` är det enda läs-/skrivlagret, med tre direkta läsare
utöver det: `/api/bot/[id]` (`handoverOf`, LiveChat), `_products.writeSyncedItems` (frånkoppling +
kopplingskontroll i samma radversion — kräver en transaktion/RPC med en tabell) och
`botStore.hasConnectedShop`. Chiffertextformatet flyttas oförändrat. Migrering = kopiera
`config.integrations` + `webhookUrl`/`webhookSecret` till tabellen, läs från båda en period, ta
sedan bort nycklarna ur `config`. Nuläget dokumenteras i README (”Integrationer — arkitektur”).

## ADR-011 — E2E-kampanj: samtals-token, conversations, signerade webhooks, ärlig copy (2026-09-02)
**Kontext:** En fullständig end-to-end-testkampanj (UI, publika API:er, ägar-API:er, billing,
scanningspipeline, ärlighet i marknadsföring/dokumentation) gav ~100 verifierade fynd som
fixades i sju parallella paket. Besluten nedan är de som formar arkitekturen framåt.
**Beslut:**
1. **Samtal räknas via serverutfärdad token ("conv").** `/api/chat/[id]` utfärdar
   `base64url(JSON{k,b,t}).HMAC_SHA256` (secret `CHAT_TOKEN_SECRET`, fallback Supabase-nyckeln;
   24 h; botbunden). Meddelande utan giltig token = nytt samtal (räknas mot planens tak, ny
   token); med giltig token = uppföljning (räknas bara som meddelande). Max 60 meddelanden
   per samtal. Widget (`sessionStorage chatbotai_conv_<botId> = {history, conv}`) och
   `/chat`-sidan skickar token på varje uppföljning. Räkningen sker atomiskt i DB via RPC
   `increment_usage` (service-rollen). *Varför:* klienten kan inte längre välja om ett
   meddelande räknas, och samtidiga anrop tappar inte räkningar.
2. **`conversations`-tabell** (RLS: ägaren läser/raderar; servern skriver). Transkript
   `[{role, content, at}]` upsertas på `conversation_key` i afterReply (best-effort, blockerar
   aldrig svaret). Arkiv/Analys/Dashboard läser den; byggarens testchattar stannar lokalt och
   visas separat, aldrig i kundsiffrorna.
3. **Träningsdata i `bots.config.training`** (`[{id, question, answer, createdAt}]`, max 200)
   via `updateBotConfig(botId, patch)` som MERGAR config (`null` tar bort en nyckel). Den
   publika chatten läser samma lista. `saveBot` mergar också, så webhook-hemligheter och
   träning överlever byggarens sparningar. localStorage-par migreras en gång.
4. **Utgående webhooks signeras med HMAC.** `X-ChatBotAI-Signature: t=<unix-s>,v1=<hex
   HMAC_SHA256(secret, t + "." + rawBody)>` — råhemligheten skickas aldrig; utan secret ingen
   header. Levereras bara när `PLANS[plan].integrations === true` (Growth/Pro).
5. **Webbsökning i chatten AV** (`CHAT_WEB_SEARCH=false`). Mätt på Autolane: domänlåst
   sökning gav fel öppettider 2 av 2 gånger och +3–7 s till första ordet. Rätt väg är att
   scanningen fångar kontakt/öppettider (crawlern prioriterar nu info-sidor). Boten säger
   ärligt "den uppgiften har jag inte" + kontaktuppgifter.
6. **Streaming överallt.** Chatten svarar via SSE (första ordet ~1,5 s), scanningens
   analyspass streamar med 8192 tokens, `stop_reason` fångas och trunkerad JSON räddas
   (`salvageJson`) + passet återupptas där det bröts.
7. **Sonnet 4.6 för chatt, Fable 5 för scanning** (ersätter ADR-009:s Opus 4.8). Uppmätt:
   samma första-ord-latens, långsammare totalt och 40 % dyrare med Opus; Sonnet svarar lika
   korrekt ur kunskapsbasen. Prompt-cache på systemprompten.
8. **Ärlig marknadsföring och dokumentation.** Inga påhittade kunder, omdömen, KPI:er,
   "15 integrationer", teammedlemmar, REST API, Klarna-/PCI-/"EU-servrar"-påståenden.
   "4 integrationer idag (widget, WordPress, webhook, Zapier) — fler på väg"; priser
   "exkl. moms" tills Stripe Tax är på; GDPR-texten säger vad som är sant (Supabase i
   eu-west-1, Anthropic i USA, Stripe hanterar kortdata) och länkar till /integritetspolicy
   och /villkor som är märkta utkast. Visitors → "Leads" (anonyma besökare spåras inte).
   *2026-09-30: alla 15 integrationer är byggda (ADR-012) — ”15 integrationer” är nu sant och
   ”kommer snart”/”Meddela mig” är borttaget; texterna följer katalogen.*
9. **Statuspolicy för plan:** planen gäller när `subscriptions.status ∈ {active, trialing,
   past_due}`, annars trial — samma regel i DB-trigger, `/api/chat`, `/api/lead` och UI.
   Trial löper ut 14 dagar efter `profiles.created_at` (admin undantagen).
10. **Säkerhetshärdningar:** trigger `profiles_protect_columns` (inloggad kan inte sätta
    `is_admin`), värdebaserad SSRF-guard (IPv4-mappad/NAT64/6to4/numeriska värdar), Stripe-
    webhook idempotent via `processed_webhook_events` och plan bara vid `payment_status=paid`,
    `/api/bot` allowlistar fält (ingen kunskapsbas), health-routes admin-only, offline-cache
    per användare som rensas vid utloggning, Stripe-checkout kräver inloggning.
**Konsekvens:** Alla ursprungliga P0-blockerare utom per-användar-tokenkvot är stängda och
verifierade. Kvar före lansering är manuella Stripe-/Vercel-/Supabase-steg och juridisk
granskning (se `TASKS.md`). Befintliga bots måste scannas om för att få den nya
kunskapsstrukturen; befintliga trial-konton äldre än 14 dagar får "begränsad"-svar tills
de får en plan.

## ADR-010 — Statusavstämning + tre P0-fixar (2026-07-01)
**Kontext:** Projektmappen återställdes från papperskorgen. En genomläsning av koden visade
att flera ADR:er beskrev önskat läge som om det vore byggt, medan `TASKS.md` å andra sidan
listade redan färdiga saker som ogjorda. Dessutom gav appen HTTP 500 vid start.
**Beslut/åtgärder:**
1. **Appstart fixad.** `postcss.config.js` refererade `tailwindcss` som PostCSS-plugin, men
   installerad Tailwind är **v4** (plugin flyttad till `@tailwindcss/postcss`) → byggfel.
   Satte `plugins: {}` (känd fungerande Vercel-config per ADR-002). Verifierat: `GET /` → 200.
2. **Webhook-signatur verifieras nu på riktigt.** `/api/webhook` anropar
   `verifyStripeSignature()` på råkroppen, fail-closed utan secret, tillämpar via
   `applyStripeEvent()`. **Detta är vad ADR-005 påstod — nu sant i routen.** Verifierat:
   osignerad POST → 400.
3. **`/api/ai` skyddat.** `sameOriginOk()` + `rateLimit()` körs först i handlern.
   Verifierat: anrop utan Origin → 403.
**Korrigering av tidigare ADR:er (läge 2026-07-01):** ADR-003:s PBKDF2 var inte implementerat
och auth var fortfarande localStorage; ADR-004 (localStorage) gällde alltjämt. *Båda är
sedan dess ersatta av Supabase Auth + Supabase-lager — se ADR-011.*
**Konsekvens:** Två P0-säkerhetshål stängda. `TASKS.md` omskriven att spegla koden.

## ADR-009 — Modellval: Fable 5 för scanning, Opus 4.8 för chatt — *chattmodellen ersatt (ADR-011)*
**Beslut:** `SCAN_MODEL = "claude-fable-5"` (djup analys/strukturering),
`CHAT_MODEL = "claude-opus-4-8"` (live-chatt). `/api/ai` faller automatiskt tillbaka till
Opus 4.8 om Fable 5 returnerar `stop_reason: "refusal"`.
**Konsekvens:** Bästa kapacitet vid scan, snabbare/billigare vid chatt. Kräver bevakning
av token-budget (se ADR-006). *2026-08-22: chatten bytte till `claude-sonnet-4-6` efter
mätning (se ADR-011 pkt 7); scanningen kör fortfarande Fable 5.*

## ADR-008 — MÄSTERSCANNER: dedikerad djup-crawler (`/api/crawl`)
**Beslut:** Egen crawler som följer sitemap/sitemap_index, expanderar listsidor + paginering,
extraherar JSON-LD/inbäddad JSON, och använder **Jina Reader** för JS-renderade SPA-sidor.
Deterministisk kort-parser plockar produkter/fordon (märke/modell/år/miltal/pris/bild) utan
AI-tokens. **Query-strängar bevaras** i länkar (annonser adresseras ofta via `?fordon=ID`).
**Kontext:** Standard-scrapern missade JS-renderat lager och query-adresserade annonser.
**Konsekvens:** Boten kan lista t.ex. "vilka Volvo finns i lager" med bilder. Beroende av
extern tjänst (Jina) för SPA — en framtida risk/kostnad. *2026-09-02: info-sidor (kontakt,
om oss, FAQ, öppettider) reserveras inom sidtaket och probas direkt; SSRF-guard + rate-limits.*

## ADR-007 — Universell (branschagnostisk) kunskapsmodell
**Beslut:** Generiskt `items[]`-schema (namn/brand/model/year/price/specs/imageUrl/...) i
stället för bil-specifik kod, plus `businessType` + `brandsInStock`.
**Konsekvens:** Fungerar för bilfirma, e-handel, restaurang, klinik m.m. med samma motor.

## ADR-006 — Anthropic via server-side proxy (`/api/ai`)
**Beslut:** Klienten anropar aldrig Anthropic direkt; `ANTHROPIC_API_KEY` finns endast i
API-routen. Retry vid 429/529, prompt-storleksdiagnostik, trimmad kunskap i prompten.
**Konsekvens:** Nyckeln läcker inte till webbläsaren. Routen skyddas av Origin-gate +
rate-limit (ADR-010). **Öppen risk:** ingen inloggningskontroll och ingen per-kund-tokenkvot;
rate-limit-storen är in-memory (se TASKS P0).

## ADR-005 — Stripe via direkt REST (utan SDK); webhook signaturverifierad
**Beslut:** `/api/checkout` skapar Checkout Session via Stripes REST-API direkt.
`/api/webhook` verifierar Stripes `stripe-signature` (HMAC-SHA256, replay-fönster
300s, konstant-tids-jämförelse) i `src/lib/stripeWebhook.js` och är **fail-closed** om
`STRIPE_WEBHOOK_SECRET` saknas. Planen sätts server-side från det verifierade eventet.
Success-sidan litar inte på `?plan=` — den anropar `/api/checkout/verify`.
**Uppdaterat 2026-09-02 (ADR-011):** planen persisteras i `subscriptions` (UPSERT via
`applyStripeEvent`), idempotens via `processed_webhook_events`, plan bara vid
`payment_status === "paid"`, användaren hittas via `metadata.user_id` → kund-id → exakt
e-post, planbyte uppdaterar befintlig prenumeration med proration, kundportal via `/api/portal`.

## ADR-004 — Persistens i `localStorage` (INTE Supabase) — *ersatt (ADR-011)*
**Beslut (historiskt):** Allt lagrades i webbläsarens `localStorage` (`chatbot-app-v2`).
**Nuläge:** Supabase Postgres är källan till sanning; `localStorage` används bara som
offline-cache per användare (rensas vid utloggning) och för byggarens testchattar.

## ADR-003 — Autentisering i klienten med PBKDF2 — *ersatt (ADR-011)*
**Beslut (historiskt):** Klient-side lösenordshash i `storage.js`. Aldrig fullt implementerat
(ADR-010). **Nuläge:** Supabase Auth med server-side sessioner, e-postbekräftelse,
lösenordsåterställning och lösenordspolicy (`passwordPolicy.js`). All localStorage-kontokod
är borttagen.

## ADR-002 — Styling med inline-styles + `globals.css` (Tailwind INTE aktivt)
**Beslut:** CSS-variabler (ljust default, `.dark`-tema) och inline-styles i komponenterna.
`tailwind.config.js` finns men `postcss.config.js` har tomma plugins → Tailwind körs inte.
**Kontext:** `@tailwindcss/postcss`-byggfel under Vercel-deploy löstes genom att tömma
postcss-pluginlistan i stället för att konfigurera Tailwind korrekt.
**Konsekvens:** **Avviker från målstacken (Tailwind).** Dokumentationen säger sedan
2026-09-02 "inline-styles". Antingen aktivera korrekt (v4) eller ta bort configfilerna.

## ADR-001 — Next.js 14 App Router i ren JSX (INTE TypeScript)
**Beslut:** Next.js 14 + React 18, allt i `.jsx`. `next.config.js` sätter
`eslint.ignoreDuringBuilds` och `typescript.ignoreBuildErrors` för att få igenom Vercel-bygget.
**Kontext:** Snabb iterering utan typuppsättning.
**Konsekvens:** **Avviker från målstacken (TypeScript).** Inga typer, lägre refaktoreringssäkerhet,
byggfel ignoreras. Migrering till TS är en P1-uppgift. (Bygget 2026-09-02 gick igenom utan fel
eller varningar.)

---

### Sammanfattning av avvikelser mot önskad stack (2026-09-30)
| Önskat | Nuläge | ADR |
|--------|--------|-----|
| TypeScript | Ren JSX (bygget grönt, men typfel ignoreras) | ADR-001 |
| Tailwind | Inline-styles + globals.css, Tailwind inaktivt | ADR-002 |
| Supabase | ✓ Postgres + Auth + RLS, källa till sanning — integrationernas tillstånd i `bots.config` i väntan på egen tabell | ADR-011/012 |
| Stripe (komplett) | ✓ Checkout, planbyte, portal, signerad + idempotent webhook — Stripe Tax/produktnamn kvar (manuellt) | ADR-005/011 |
| Vercel | ✓ deployad — Deployment Protection måste stängas av (widget, kanaler, Stripe) | — |
| Claude API | ✓ via server-proxy, Sonnet 4.6 chatt + kanaler / Fable 5 scan, streaming — kontot saknar kredit 2026-09-30 | ADR-006/011 |
