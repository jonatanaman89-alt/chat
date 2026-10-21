# ChatBot AI — SaaS Platform

AI-chatbot för svenska småföretag. Kunden anger sin hemsida → plattformen scannar sajten
och bygger en kunskapsbas → boten svarar kundens besökare dygnet runt via en chattwidget
(en rad kod) eller en delningslänk. Svenskt UI, priser i kr/mån, betalning via Stripe.

## Snabbstart

```bash
# 1. Installera dependencies
npm install

# 2. Lägg miljövariabler i .env.local (se listan nedan)

# 3. Kör databas-schemat i Supabase (Dashboard → SQL Editor → klistra in supabase/schema.sql → Run)

# 4. Starta dev-server
npm run dev

# 5. Öppna http://localhost:3000
```

### Miljövariabler

**Hela listan — varje variabel koden läser, var värdet kommer ifrån och vad som händer utan den —
finns i `.env.example`.** Tabellen nedan är de viktigaste.

| Variabel | Används till |
|----------|--------------|
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (eller `…_ANON_KEY`) | Supabase-klient i webbläsaren (RLS gäller) |
| `SUPABASE_SECRET_KEY` (eller `SUPABASE_SERVICE_ROLE_KEY`) | Server-side admin-klient (webhook, /api/chat, adminpanel) |
| `INTEGRATIONS_ENC_KEY` | Rekommenderas: egen nyckel (32 slumpade byte, base64) som krypterar integrationernas hemligheter (tokens, API-nycklar, webhook-URL:er). **Samma värde i alla miljöer som delar databasen** — `.env.local` och Vercel använder samma Supabase-projekt. Saknas den krypteras de med Supabase-nyckeln ovan — byts den nyckeln kan sparade kopplingar inte läsas (ägaren ser ”anslut igen”). Byte till egen nyckel: sätt `INTEGRATIONS_ENC_KEY` och låt Supabase-nyckeln vara kvar; hemligheterna flyttas till den nya nyckeln när respektive koppling används eller sparas (se ”Integrationer — arkitektur”) |
| `PUBLIC_APP_URL` | Publik https-adress (produktionens origin) som kanalernas Callback-URL:er byggs av — Telegram och Meta skickar kundmeddelanden dit. Saknas den används `NEXT_PUBLIC_DOMAIN`, sedan Vercels produktionsdomän (`VERCEL_PROJECT_PRODUCTION_URL`). Adresser som inte är https eller pekar på localhost räknas inte: från localhost sparas en kanal som ”väntar” |
| `ANTHROPIC_API_KEY` | AI-scanning, livechatt och kanalernas svar (bara server-side: `/api/ai`, `/api/chat`, `/api/channels/…`) samt adminpanelens AI-kontroll — när Anthropic är AI-leverantör (standard) |
| `NEXT_PUBLIC_AI_PROVIDER`, `OPENAI_API_KEY`, `GEMINI_API_KEY` | Valfritt: `openai` byter AI-leverantör till OpenAI (kräver `OPENAI_API_KEY`), `gemini` till Google Gemini (kräver `GEMINI_API_KEY`; gratisnivån, bara för test), `vertex` till Gemini på Google Cloud Vertex AI (se nästa rad). Utan variabeln används Anthropic. Se ”Byta AI-leverantör” |
| `GOOGLE_SERVICE_ACCOUNT_JSON`, `GCP_PROJECT_ID`, `GCP_LOCATION` | Bara med `NEXT_PUBLIC_AI_PROVIDER=vertex`: hela JSON-nyckeln för ett Google Cloud-tjänstekonto (hemlig, bara server-side), projektets ID (standard: nyckelns `project_id`) och platsen (`eu` som standard). Valfritt `VERTEX_CHAT_MODEL` / `VERTEX_SCAN_MODEL` (och `VERTEX_ALLOW_PREVIEW=1` för förhandsmodeller). Se ”Gemini på Google Cloud Vertex AI” |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_STARTER/GROWTH/PRO` | Checkout, kundportal, webhook |
| `NEXT_PUBLIC_DOMAIN` | Äldre namn på den publika adressen — läses efter `PUBLIC_APP_URL` (Stripes retur-URL:er, mejllänkar, inbäddningskoden, canonical) |
| `STRIPE_AUTOMATIC_TAX` | `true` först när Stripe Tax är aktiverat: Checkout lägger då på moms, tar in momsregistreringsnummer och kräver faktureringsadress |
| `STRIPE_CHECKOUT_ENABLED`, `STRIPE_ALLOW_TEST_MODE` | Lanseringsspärren (se ”Betalningar: lanseringsspärr”): `STRIPE_CHECKOUT_ENABLED=false` stänger alla nya köp (nödbroms); `STRIPE_ALLOW_TEST_MODE=1` tillåter testköp i produktion — bara för en egen kort test |
| `CHAT_TOKEN_SECRET`, `CRON_SECRET` | HMAC-hemlighet för samtals-token (faller annars tillbaka på Supabase-nyckeln) och nyckeln för Vercels cron-jobb (utan den svarar cron 503). Läggs in i Vercel med `scripts/setup-secrets.ps1` |
| `RESEND_API_KEY`, `EMAIL_FROM`, `ALERT_EMAIL` | E-post (leadnotiser, larm, flyttinbjudningar) via Resend; utan nyckel/avsändare skickas inga mejl. `ALERT_EMAIL` = vart driftlarm går |
| `ADMIN_EMAIL` | Bara server-side: adminkontroll vid sidan av `profiles.is_admin` och standardmottagare för larm (standard i `src/lib/adminEmail.js`) |
| `LEGAL_UPDATED` | `ÅÅÅÅ-MM-DD`: "Senast uppdaterad" på integritetspolicyn och villkoren när det är senare än kodens datum — sätt den dagen ett byte av AI-leverantör går live |
| `DEMO_BOT_IDS` | Botar (kommaseparerade id:n) som undantas från trial-utgången, t.ex. demoboten på egna sajten |
| `ALLOWED_ORIGINS` | Extra tillåtna origins för ägar-routes (kommaseparerad) |
| `NEXT_PUBLIC_CONTACT_EMAIL` | Kontaktkolumn i sidfoten + kontaktrad på /integritetspolicy och /villkor |
| `AI_RATE_LIMIT`, `AI_USER_RATE_LIMIT`, `CRAWL_RATE_LIMIT`, `CRAWL_PAGE_RATE_LIMIT`, `CRAWL_USER_RATE_LIMIT`, `CRAWL_USER_PAGE_RATE_LIMIT` | Valfria överstyrningar av rate-limits (per IP och per inloggad användare) |

## Deploya till Vercel

```bash
npm i -g vercel
vercel
```

Lägg in samma miljövariabler i Vercel, plus `PUBLIC_APP_URL` (och helst `INTEGRATIONS_ENC_KEY`
med **samma** värde som i `.env.local`). `CHAT_TOKEN_SECRET`, `CRON_SECRET`, `PUBLIC_APP_URL` och
(valfritt) `NEXT_PUBLIC_CONTACT_EMAIL` / `ALERT_EMAIL` lägger skriptet in åt dig — nycklarna slumpas
och visas aldrig, och en befintlig nyckel byts bara med `-Rotate`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-secrets.ps1 -ContactEmail du@exempel.se -AlertEmail du@exempel.se
```

Serverfunktionerna körs i Vercels region **dub1 (Dublin)**, bredvid Supabase (eu-west-1) —
`"regions"` i `vercel.json`. Integritetspolicyns Vercel-rad säger samma sak; ändra båda tillsammans.
Säkerhetsrubrikerna (ingen inramning av sidorna, `nosniff`, `Referrer-Policy`) sätts i
`next.config.js` → `headers()`. **Stäng av Deployment Protection** (Vercel → Settings →
Deployment Protection) — annars svarar `/api/chat` och `/api/bot` 401 för anonyma besökare och
widgeten fungerar inte — och varken Telegram/Meta (`/api/channels/…`) eller Stripe (`/api/webhook`)
når appen. Peka Stripes webhook på `https://<domän>/api/webhook`. Kanalmeddelanden och leads
besvaras direkt och arbetet efteråt (AI-svar, notiser) körs vidare med `waitUntil` från
`@vercel/functions` (`src/lib/background.js`).

Lokalt och i produktion används **samma Supabase-databas**: en koppling som ansluts eller kopplas
från på localhost gäller även produktionen.

## Byta AI-leverantör (Anthropic ↔ OpenAI ↔ Gemini ↔ Vertex AI)

Standard är **Anthropic**. Allt AI-arbete — kundchatten, kanalerna, scanningen, byggarens
testchatt och adminpanelens AI-kontroll — går genom `src/lib/anthropic.js`. Med
`NEXT_PUBLIC_AI_PROVIDER=openai` lämnar den varje anrop till `src/lib/openaiChat.js` (samma
prompt, kunskapsbas och svarsregler; samma felhantering). **Samma variabel** styr vilken
leverantör integritetspolicyn, villkoren och startsidan nämner (`src/lib/aiProviderInfo.js`),
så texterna alltid säger vem som faktiskt tar emot besökarnas meddelanden.

Slå på OpenAI:
1. Skapa en API-nyckel på platform.openai.com och fyll på krediter (Settings → Billing).
2. Lokalt: lägg till `OPENAI_API_KEY=…` och `NEXT_PUBLIC_AI_PROVIDER=openai` i `.env.local`,
   starta om `npm run dev`.
3. Vercel: lägg in samma två variabler och **gör en ny deploy** — `NEXT_PUBLIC_`-variabler bakas
   in vid bygget, så en ändring gäller först efter redeploy.
4. Kontrollera: Admin → AI-status ska visa att OpenAI svarar; ställ en fråga i widgeten.

Valfritt: `OPENAI_CHAT_MODEL` (kundchatt) och `OPENAI_SCAN_MODEL` (scanning m.m.), båda
`gpt-6.1-sol` som standard; `OPENAI_CHAT_REASONING` (`low`) och `OPENAI_SCAN_REASONING`
(`medium`); `OPENAI_BASE_URL` för en annan OpenAI-kompatibel tjänst.

Bra att veta:
- Bara `OPENAI_API_KEY` byter ingenting — variabeln måste sättas. Ett okänt värde (stavfel) ger
  Anthropic och en varning i serverloggen; en gammal `AI_PROVIDER` ignoreras (med varning).
- `ANTHROPIC_API_KEY` behövs inte när OpenAI är vald, men kan ligga kvar. Byta tillbaka: ta bort
  variabeln (eller sätt `anthropic`) och deploya igen.
- AI-leverantören är ett underbiträde: meddela kunderna före bytet och uppdatera datumet i
  integritetspolicyn. Pekar `OPENAI_BASE_URL` på en annan leverantör stämmer inte
  texten ”OpenAI (USA)” — då måste sidorna ändras (för Gemini: använd `gemini` nedan). Webbsökning
  i chatten (avstängd idag) fungerar bara mot api.openai.com.

### Google Gemini på gratisnivån (för test och demo i väntan på krediter)

`NEXT_PUBLIC_AI_PROVIDER=gemini` + `GEMINI_API_KEY` (skapas på aistudio.google.com → Get API key)
kör allt via Googles OpenAI-kompatibla API (`src/lib/openaiChat.js`). Standardmodeller:
`gemini-3.5-flash-lite` för kundchatten och `gemini-3.8-flash` för scanning; ändra med
`GEMINI_CHAT_MODEL` / `GEMINI_SCAN_MODEL` (och `GEMINI_CHAT_REASONING` `low` /
`GEMINI_SCAN_REASONING` `medium`). Sätt variablerna i Vercel och gör en ny deploy.

Bra att veta (Googles villkor och dokumentation, kontrollerade 2026-10-03):
- **Bara för test.** Gemini API:s villkor tillåter bara betaltjänsten när en tjänst görs
  tillgänglig för användare i EES (Sverige), Schweiz eller Storbritannien. Villkoren för
  gratisnivån låter Google använda innehållet för att förbättra sina tjänster och granskare läsa
  det (för utvecklare i EES gäller enligt samma villkor i stället betaltjänstens dataregler) och
  säger: skicka inga känsliga, konfidentiella eller personliga uppgifter. Alltså inga riktiga
  kunders samtal. Landningssidans demo är **avstängd** så länge `gemini` är vald och
  `NEXT_PUBLIC_DEMO_ENABLED` inte är satt (`true` slår på den ändå). Admin → AI-status visar en
  varning så länge `gemini` är vald, och integritetspolicyn säger hur Google kan använda innehållet.
- Läget förutsätter **gratisnivån** (projekt utan fakturering). Slår du på fakturering i AI Studio
  blir det betaltjänsten — då stämmer inte integritetspolicyns gratisnivå-text, Admin-varningen
  eller kvottexterna, och de måste ses över först.
- Kvoterna är små och gäller per projekt; dagskvoten återställs vid midnatt Stillahavstid
  (normalt kl. 09 svensk tid). Slut på kvot räknas som ”Anropsgräns” (inte ”slut på krediter”);
  besökarna får det vanliga ”försök igen”-svaret, byggarens scanning och testchatt säger att
  gratisnivåns kvot är slut (bara en minutkvot väntas ut — en dagskvot stoppar direkt), och den
  automatiska omskanningen behåller den gamla kunskapen och försöker igen nästa natt.
  Se förbrukningen på aistudio.google.com/rate-limit.
- Webbsökning finns inte (ingen Responses API, och sökgrundning ingår inte i gratisnivån) —
  scanningens nödväg via webbsökning säger då att den inte stöds.

### Gemini på Google Cloud Vertex AI (riktiga besökare, betalas med Google Clouds provperiod)

`NEXT_PUBLIC_AI_PROVIDER=vertex` kör allt via Vertex AI:s OpenAI-kompatibla API
(`src/lib/openaiChat.js`) med ett tjänstekonto (`src/lib/googleAuth.js` gör om nyckeln till en
OAuth-token som gäller en timme och cachas). Det är en **betald Google Cloud-tjänst** — Google
Clouds Free Trial (300 USD i 90 dagar) betalar för den — under Google Clouds villkor: Google är
personuppgiftsbiträde (Cloud Data Processing Addendum) och tränar inte modeller på uppgifterna
(Service Specific Terms §18). Därför finns ingen gratisnivå-varning och demon är på som vanligt.
Fakta och källor (kontrollerade 2026-10-04): scratchpad `vertex/FACTS.md`.

**Snabbaste vägen: kör `scripts/setup-vertex.ps1`.** Själv gör du bara två saker: startar Free Trial i
webbläsaren (console.cloud.google.com/freetrial — Sverige, Individual; klicka aldrig på ”Upgrade”) och
installerar Google Cloud CLI en gång (`winget install -e --id Google.CloudSDK`). Kör sedan i projektmappen

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-vertex.ps1
```

och logga in hos Google när webbläsaren öppnas. Skriptet gör resten: väljer provperiodens
faktureringskonto, skapar projektet `chatbot-ai-…` (eller återanvänder det från en tidigare körning;
`-ProjectId` väljer ett eget), kopplar faktureringen, aktiverar Agent Platform API, skapar tjänstekontot
`chatbot-ai` med rollen Agent Platform User och en JSON-nyckel, skriver `GOOGLE_SERVICE_ACCOUNT_JSON`
(base64), `GCP_PROJECT_ID` och `GCP_LOCATION=eu` i `.env.local` och i Vercel (Production; nyckeln som
Sensitive, via stdin), lägger ett budgetlarm (mejl vid ≈ 50/150/250 USD — provperiodens kredit räknas inte
av, annars går larmet aldrig) och gör ett testanrop (`node scripts/vertex-smoke.mjs`, går också att köra
separat; annan env-fil: `--env <fil>`). Nyckeln skrivs aldrig ut och den tillfälliga nyckelfilen raderas
direkt (även vid Ctrl+C eller stängt fönster). Skriptet sätter **inte** `NEXT_PUBLIC_AI_PROVIDER` — det görs
efter testet, följt av en ny deploy. Säkert att köra igen: det som finns återanvänds, även nyckeln i
`.env.local` så länge den gäller hos Google (`-NewKey` skapar en ny; Google tillåter högst 10 per
tjänstekonto och skriptet tar aldrig bort någon). Fel Google-konto: kör med `-SwitchAccount`. Gick bara
testanropet inte igenom (Google sprider nya behörigheter på ”typically 2 minutes, potentially 7 minutes or
longer”; testet väntar högst ca 8 minuter): vänta
några minuter och kör `node scripts/vertex-smoke.mjs` — inte hela skriptet. Stegen nedan är samma sak
för hand.

Slå på:
1. console.cloud.google.com → starta Free Trial (kort krävs, men inget dras under provperioden) och
   skapa ett projekt. Notera projektets **ID** (inte namnet).
2. API:er och tjänster → Bibliotek → aktivera **Agent Platform API** (hette tidigare Vertex AI API;
   `aiplatform.googleapis.com`, direktlänk: console.cloud.google.com/apis/library/aiplatform.googleapis.com).
3. IAM och administration → Tjänstkonton → skapa ett konto, ge det rollen **Agent Platform User**
   (`roles/aiplatform.user`) → Nycklar → Lägg till nyckel → JSON. (Organisationer skapade efter
   maj 2024 blockerar nyckelskapande som standard — ett vanligt Google-konto utan organisation gör det inte.)
4. Vercel: `NEXT_PUBLIC_AI_PROVIDER=vertex`, `GCP_PROJECT_ID=<projekt-ID>`, `GCP_LOCATION=eu` och
   `GOOGLE_SERVICE_ACCOUNT_JSON=<hela JSON-filen>` (eller samma fil base64-kodad) → **ny deploy**
   (`NEXT_PUBLIC_AI_PROVIDER` och `GCP_LOCATION` bakas in vid bygget).
5. Kontrollera: Admin → AI-status ska visa ”Google Cloud Vertex AI: OK” med projekt, plats och modeller.

Standardmodeller: `google/gemini-3.5-flash-lite` (kundchatt, reasoning `low`) och
`google/gemini-3.8-flash` (scanning, `medium`), båda GA. Ändra med `VERTEX_CHAT_MODEL` /
`VERTEX_SCAN_MODEL` (”gemini-…” får prefixet `google/` automatiskt) och `VERTEX_CHAT_REASONING` /
`VERTEX_SCAN_REASONING`.

Bra att veta:
- **Platsen styr vad sidorna säger.** `eu` (rekommenderas) = Googles EU-multiregion: Google håller
  behandlingen inom EU:s medlemsländer, och integritetspolicyn/startsidan säger ”EU”. Dagens Gemini
  3-modeller finns **inte** i enskilda europeiska regioner som `europe-north1` eller `europe-west4`
  (bara `eu`, `us` och `global`). `global` ger störst kapacitet men ingen garanti om var svaren tas
  fram — sidorna säger då ”olika länder”. Region utanför EU (t.ex. London) nämns vid namn.
- **Provperioden tar slut** efter 90 dagar eller när 300 USD är förbrukade. Uppgraderar du inte till
  ett betalkonto innan dess stänger Google faktureringskontot och stoppar projektet: alla AI-anrop
  får då 403 BILLING_DISABLED, vilket räknas som ”Slut på krediter” (besökarna får ”chatten är
  tillfälligt ur funktion” med företagets kontaktuppgifter, larmet går direkt). Admin → AI-status
  påminner om detta och länkar till Fakturering.
- Fel som måste åtgärdas i Google Cloud (API inte aktiverat, roll saknas, nyckel borttagen, modell
  som inte finns på platsen, fakturering) visas med exakt åtgärd i Admin, i larmmejlet och i
  byggarens scanning/testchatt **när du är inloggad som admin**. Kunderna ser i byggaren bara en
  neutral text (”AI-tjänsten är tillfälligt ur funktion …”) — de kan inte åtgärda det, och texterna
  nämner plattformens projekt. 429 betyder tillfällig kapacitetsbrist (inte en fast kvot) och prövas
  om automatiskt; projekt i provperioden kan inte få högre kvoter.
- **Googles regler för generativ AI** (Service Specific Terms §20 d–e) gäller även kundernas botar:
  ingen användning på webbplatser som riktar sig till eller sannolikt besöks av personer under 18 år,
  och inte för kliniska ändamål eller som ersättning för medicinsk rådgivning (bokning och andra
  administrativa frågor går bra). Google kan stänga av tjänsten vid misstänkta överträdelser.
  Användarvillkoren (avsnitt 6) för vidare reglerna när `vertex` är valt — utkast, granskas av jurist.
- Förhandsmodeller (”preview”/”exp”) omfattas inte av Googles personuppgiftsvillkor. Står en sådan i
  `VERTEX_CHAT_MODEL` / `VERTEX_SCAN_MODEL` används den **inte** (botarna kör standardmodellen och
  Admin säger det) — om du inte sätter `VERTEX_ALLOW_PREVIEW=1`; då säger integritetspolicyn att
  personuppgifter inte ska skrivas i chatten och bär en jurist-markering. Webbsökning stöds inte (kan
  inte begränsas till kundens domän eller hållas i EU).
- AI-leverantören är ett underbiträde: uppdatera datumet i integritetspolicyn och meddela kunderna
  före bytet, som vid andra byten. Samma sak om du byter `GCP_LOCATION` till en plats utanför EU
  (t.ex. `global`): policyn nämner då överföringen utanför EU/EES.

## Funktioner

- **Landing page** — ärlig marknadsföring (inga påhittade kunder/omdömen), priser exkl. moms, FAQ
- **Konto** — Supabase Auth (e-post + lösenord, e-postbekräftelse, glömt lösenord), 14 dagars trial
- **Dashboard** — get-started-guide, bot-lista, verklig månadsstatistik från databasen, och en
  varning per bot när dess AI-svar misslyckas (t.ex. slut på AI-kredit — `bots.config.aiStatus`)
- **Bot Builder** — AI-scanning av hemsidan (djup crawler + streamade analyspass), utseende,
  hälsning, snabbsvar (max 6), live testchatt
- **Träning** — egna fråga/svar-par (sparas i `bots.config.training`, används av den publika chatten)
- **Embed** — `<script src="<app-origin>/widget.js" data-bot-id="…" async>` — widgeten serveras
  från appens egen origin (`public/widget.js`) och läser position/utseende från bot-configen
- **Delningslänk** — `/chat?bot=<id>` som publik chattyta
- **Leads** — kontaktuppgifter som boten samlar in (sök, datum- och botfilter)
- **Arkiv** — riktiga kundsamtal från `conversations`-tabellen, märkta med källa (hemsida,
  delningslänk, Telegram, WhatsApp, Messenger, Instagram — `SOURCE_LABELS` i katalogen) + lokala testchattar
- **Analys** — konversationer/meddelanden per månad från `usage`, diagram från `conversations`
- **Integrationer** — 15 st, alla live (katalog: `src/lib/integrations/catalog.js`). Alla planer:
  hemsida (widget), WordPress, Shopify och WooCommerce (produktsynk till kunskapsbasen). Growth/Pro:
  Telegram, WhatsApp, Messenger och Instagram (kunder chattar med boten där), Slack och Discord
  (notiser), Zendesk och Freshdesk (ärenden), LiveChat (överlämning till människa), webhook
  (HMAC-signerad) och Zapier. Sidan har botväljare, sammanfattning, kategorifilter + sök och en
  detaljsida per integration (steg, formulär, status, Callback-URL/Verifieringstoken för kanaler).
  Varje koppling visar status och senaste fel; en koppling som inte fungerar märks ”Behöver
  åtgärd”. Se ”Integrationer — arkitektur” nedan
- **Priser & Fakturering** — Stripe Checkout, planbyte med proration, Stripe kundportal
  ("Hantera prenumeration"), användningsmätare mot planens tak
- **Inställningar** — profil (namn, företag, telefon), mörkt/ljust tema
- **Adminpanel** — bara för `profiles.is_admin` (server-side kontroll): användare, MRR, AI-status
  (Anthropic-kontroll + botar vars AI-svar misslyckas), historiska intresseanmälningar från tiden
  innan alla integrationer fanns (`integration_interests`, inga nya tillkommer)
- **Juridik** — `/integritetspolicy` och `/villkor` (utkast, märkta "låt jurist granska")

## Integrationer — arkitektur

Katalog → API → providers. Det sidan visar och det servern tillåter kommer från samma lista.

```
catalog.js ──► IntegrationsPage (components/integrations/*) ──► /api/integrations ──► providers/<id>.js
                                                                     │  connect/test/verify/sync/disconnect
                                                                     ▼
                                                   bots.config.integrations[<id>]  (store.js, krypterade hemligheter)
                                                                     ▲
/api/channels/<provider>/<botId> ──► provider.inbound ──► botEngine.js (samma hjärna som /api/chat)
/api/lead, /api/chat, botEngine  ──► dispatch.js ──► provider.deliver (webhook, Zapier, Slack, Discord, Zendesk, Freshdesk)
```

- **Katalog** — `src/lib/integrations/catalog.js` (klient + server): 15 integrationer i 6 kategorier
  med `kind` (install, commerce, channel, notify, ticket, handover, webhook), `plan` (`all` eller
  `growth`), formulärfält, steg, `actions` och texter. Sidan renderas helt från katalogen + serverns
  status. Katalogtexterna får bara lova det providern faktiskt gör.
- **API** — `/api/integrations` (inloggad ägare via Bearer-token eller cookie-session; boten måste
  vara ägarens, annars 404). `GET ?botId=` → publik status för alla 15 + `planKey` + publik origin.
  `POST { botId, id, action, input }` där `action` ∈ katalogens `actions`: `connect`, `test`, `verify`
  (installationskontroll), `sync` (produktsynk), `disconnect`. Same-origin + 30 anrop/min per
  användare. Growth-integrationer ger 403 (`locked`) på Trial/Starter — utom `disconnect`.
- **Providers** — `src/lib/integrations/providers/<id>.js`, laddas lazy via `providers/index.js`
  (`connect`, `test`, `verify`, `sync`, `disconnect`, `deliver`, `inbound`). Delade hjälpare:
  `_meta.js` (WhatsApp/Messenger/Instagram), `_format.js` (notiser/ärenden), `_products.js`
  (produktsynk), `_install.js` (letar efter widget-koden på ägarens sida). `http.js`: `apiFetch`
  för fasta API-värdar, `safeFetch` (SSRF-kontroll per hopp + `guardedFetch`) för adresser ägaren anger.
- **Lagring** — `bots.config.integrations[<id>]` = `{ enabled, status, settings, secrets,
  secretHints, info, message, lastError, lastErrorAt, lastEventAt, connectedAt, updatedAt }`
  (`store.js`; varför i `config` och inte egen tabell: ADR-012). Den äldre webhooken ligger kvar i
  `config.webhookUrl`/`webhookSecret`. Nycklarna `integrations`, `webhookUrl` och `webhookSecret`
  skrivs bara av servern — `botStore.js` tar bort dem ur appens bot-objekt och skriver aldrig
  tillbaka dem. Alla skrivningar är compare-and-swap på `bots.updated_at` (trigger
  `bots_touch_updated_at`), så byggarens sparningar och serverns statusskrivningar inte skriver över
  varandra.
- **Kryptering och nyckelrotation** — `secrets` är AES-256-GCM-krypterad JSON (`crypto.js`, format
  `enc:v2:<nyckel-id>:…`); webbläsaren får bara ledtrådar (”…AbC1”). Nyckelringen är
  `INTEGRATIONS_ENC_KEY` → `SUPABASE_SECRET_KEY` → `SUPABASE_SERVICE_ROLE_KEY`: den första som är
  satt krypterar, alla som är satta kan dekryptera. Värden under en äldre nyckel krypteras om när
  kopplingen används eller sparas; den gamla nyckeln kan tas bort först när inget gammalt finns
  kvar. Ett värde som ingen konfigurerad nyckel kan öppna visas som ”anslut igen”.
- **Inkommande kanaler** — `GET|POST /api/channels/<provider>/<botId>` (telegram, whatsapp,
  messenger, instagram). Providern verifierar anropet (Telegrams `X-Telegram-Bot-Api-Secret-Token`;
  Metas `hub.verify_token`-handskakning och `X-Hub-Signature-256`), deduplicerar på meddelande-id i
  `processed_webhook_events` och svarar 200 direkt. Svaret tas fram i bakgrunden av `botEngine.js` —
  samma prompt, modell, träning och plan-/samtalstak som `/api/chat` — och sparas i `conversations`
  (nyckel `<provider>:<botId>:<avsändare>:…`, källa = kanalen) och `usage`. Rate-limits per IP, bot
  och avsändare. Callback-URL:en byggs av den publika https-adressen (`PUBLIC_APP_URL`); utan en
  sådan (localhost) sparas kanalen som ”väntar”. Telegram registrerar webhooken själv vid anslut;
  Meta-kanalerna blir ”Ansluten” när Meta har verifierat Callback-URL + Verifieringstoken.
- **Händelser ut** — `dispatchEvent()` (`dispatch.js`) skickar `lead.created` (från `/api/lead`)
  och `conversation.started` (nytt samtal i `/api/chat` eller en kanal) till webhook + Zapier (alla
  händelser) och Slack, Discord, Zendesk, Freshdesk (de händelser ägaren kryssat i). Bara när ägarens
  plan har integrationer; parallellt, ≤ ~5 s, efter svaret till besökaren; utfallet
  (`lastEventAt`/`lastError`) sparas i en skrivning. Kuvertet och `X-ChatBotAI-Signature` är samma
  som i `src/lib/webhook.js`.
- **Produktsynk** — Shopify (butikens publika produkt-JSON, ingen app/nyckel) och WooCommerce (Store
  API; REST v3 med läsnycklar bara om Store API är avstängt) hämtar upp till 500 produkter och
  ersätter butikens poster i `bots.knowledge.items` (`source: "shopify"|"woocommerce"`, CAS på
  `updated_at`). Priser skrivs bara i den valuta butiken själv visar. En ny scanning i byggaren
  behåller synkade produkter; ”Koppla från” tar bort dem.
- **LiveChat-överlämning** — `/api/bot/[id]` lägger till `handover: { provider, license, label }`
  (det enda ur `config.integrations` som någonsin blir publikt) när LiveChat är ansluten och ägarens
  plan har integrationer (cachas upp till 5 min). `widget.js` visar då ”Prata med en människa”,
  öppnar LiveChats widget på samma sida och skickar med besökarens senaste fråga; delningslänken
  öppnar LiveChats chattsida i en ny flik.
- **AI-hälsa** — `aiHealth.js` sparar utfallet av AI-anropen (`/api/chat` och kanalerna) i
  `bots.config.aiStatus`: bara vid växling ok ↔ fel, och högst var 5:e minut under ett avbrott.
  Dashboard varnar per bot, Admin visar AI-status med en liten live-kontroll mot den aktiva
  AI-leverantören (Anthropic eller OpenAI, se ”Byta AI-leverantör”), och en
  kanal visar felet som kopplingens ”Senaste fel”.

## Tech Stack

- **Next.js 14** (App Router) + **React 18** — ren **JSX** (ingen TypeScript)
- **Inline-styles + `src/styles/globals.css`** (CSS-variabler, `.dark`-tema) — Tailwind är **inte** aktivt
- **Supabase** — Postgres (källan till sanning för konton, bots, planer, leads, samtal, användning),
  Supabase Auth, Row Level Security + kolumnskydd via trigger
- **Anthropic Claude API** — `claude-fable-5` för scanning, `claude-sonnet-4-6` för livechatt
  (streaming + prompt-cache, webbsökning avstängd efter mätning); OpenAI kan väljas i stället
  med `NEXT_PUBLIC_AI_PROVIDER=openai` (se ”Byta AI-leverantör”)
- **Stripe** (REST direkt, ingen SDK) — Checkout, prenumerationsuppdatering, Billing Portal,
  signaturverifierad webhook med idempotens
- **Vercel** — hosting

## Filstruktur

```
public/widget.js            — Embed-widgeten (serveras från appens origin)
supabase/schema.sql         — Hela databasens slutläge: tabeller, RLS, triggers, RPC (idempotent)
supabase/migrations/        — Ändringshistoriken, en fil per migrering (se README där)
src/
  middleware.js             — Inloggningsgrind (cookie-kontroll, inga nätverksanrop): /, /login, /signup, /app/*
  app/
    layout.jsx              — Root layout
    page.jsx                — Server-renderad landningssida (+ LandingClient.jsx)
    app/                    — Appen under /app (layout → components/AppShell.jsx, URL:er i lib/routes.js)
    login/, signup/         — Inloggning och registrering
    robots.js, sitemap.js   — SEO
    not-found.jsx           — 404
    chat/page.jsx           — Publik chattyta (delningslänk)
    checkout/page.jsx       — Stripe-retur (verifierar betalning via /api/checkout/verify)
    reset-password/page.jsx — Återställ lösenord
    integritetspolicy/, villkor/ — Juridiska sidor (utkast)
    api/
      ai/                   — Anthropic-proxy för scanning (Origin-gate + rate-limit, SSE)
      crawl/                — HTTP-skal runt src/lib/crawler.js (djup crawler, delad av /api/crawl, omskanning och demo)
      cron/rescan/          — Veckovis automatisk omskanning (Vercel Cron, kräver CRON_SECRET)
      demo/                 — Landningsdemon (scan, chat) + cleanup (Vercel Cron)
      waitlist/, admin/waitlist/ — Väntelista (publik anmälan, admin-vy)
      bot/[id]/             — Publik bot-config för widgeten (allowlistade fält, ingen kunskapsbas)
      chat/[id]/            — Publik chatt (SSE), samtals-token, plan-/trial-/samtalstak, träningsdata
      chat/[id]/feedback/   — Besökarens tumme upp/ner på ett svar
      lead/                 — Leads från widget/delningslänk
      checkout/, checkout/verify/, portal/ — Stripe (kräver inloggning)
      webhook/              — Stripe-webhook (signerad, idempotent)
      integrations/         — Ägarens integrationer per bot: GET status, POST connect/test/verify/sync/disconnect
      channels/[provider]/[botId]/ — Inkommande meddelanden från Telegram/WhatsApp/Messenger/Instagram
      admin/stats/          — Adminpanelens data (403 för icke-admin)
      health/               — Schema-/Supabase-hälsokontroll (admin-only)
  components/               — Sidvyer (Dashboard, BotBuilder, Training, Embed, Integrations,
                              Visitors (Leads), Archives, Analytics, Pricing, Billing, Settings, Admin …)
    integrations/           — Integrationssidans delar (översikt, kort, detaljsida, formulär, statuspanel)
  lib/
    ai.js                   — scanWebsite()/runScan() + liveChat() (orkestreringen; servern kör samma runScan)
    crawler.js, scanServer.js, autoRescan.js — Crawler (server only), serverns omskanning, omskanningens regler
    routes.js               — Sidnyckel ↔ URL för appen
    leads.js, contactCapture.js, notify.js, email.js — Leads (även ur chatten), lead-mejl, AI-larm (Resend)
    noAnswer.js, trainingInsights.js, feedbackStore.js — Obesvarade frågor och tumme ner → Träning
    demo.js                 — Landningsdemon (server only)
    chatPrompt.js           — Systemprompt för chatten (KRITISK REGEL — LÄSES FÖRST + retrieval)
    anthropic.js            — Server-side AI-anrop (callAnthropic / streamAnthropic) — lämnar över
                              till openaiChat.js när NEXT_PUBLIC_AI_PROVIDER=openai
    openaiChat.js           — OpenAI-adapter med exakt samma kontrakt (in-/utdata, felklasser)
    aiProviderInfo.js       — Vilken AI-leverantör som gäller (namn, land, konsol) — server + klient
    constants.js            — PLANS, PLAN_FEATURES, modellnamn (importeras av klienten)
    adminEmail.js           — ADMIN_EMAIL, bara server-side
    botStore.js, leadStore.js, profileStore.js, conversationStore.js — Supabase-datalager
    integrations/           — catalog.js (de 15 integrationerna), store.js (lagring i bots.config),
                              crypto.js (krypterade hemligheter), dispatch.js (händelser ut), providers/*
    integrationsClient.js   — Integrationssidans anrop mot /api/integrations
    botEngine.js, ownerPlan.js, transcript.js — Kanalernas svarsmotor (samma som /api/chat), plan/tak, samtalslagring
    aiHealth.js             — bots.config.aiStatus: fungerar botens AI-svar? (Dashboard + Admin)
    background.js           — runInBackground(): arbete efter svaret (Vercel waitUntil)
    supabase/               — client.js (webbläsare), server.js (cookies), admin.js (service-role)
    convToken.js            — Signerad samtals-token
    apiGuard.js             — sameOriginOk + rate-limit (in-memory)
    ssrf.js                 — URL-/IP-validering för crawl, integrationer och webhooks (även vid anslutning: DNS-rebinding)
    webhook.js              — Utgående webhooks (HMAC-signatur)
    stripe-config.js, stripeWebhook.js, subscriptions.js — Stripe server-side
    checkoutGate.js         — Lanseringsspärren: får ett köp startas? (test/live, produktion)
    adminAuth.js            — Admin-kontroll från sessionen (profiles.is_admin)
    storage.js              — Kvarvarande localStorage (offline-cache per användare, testchattar)
  styles/globals.css        — CSS-variabler + micro-interactions
```

## Priser (exkl. moms)

Definieras i `src/lib/constants.js` (`PLANS`). Stripe-priser via `STRIPE_PRICE_*`.

| Plan | Pris/mån | Bots | Konv/mån | Growth-integrationer* |
|------|----------|------|----------|----------------|
| Trial | 0 kr (14 dagar) | 1 | 100 | – |
| Starter | 699 kr | 2 | 1 000 | – |
| Growth | 1 599 kr | 5 | 5 000 | ✓ |
| Pro | 4 699 kr | 15 | 25 000 | ✓ |

\* Kanaler, notiser, ärenden, LiveChat, webhook och Zapier. Hemsida, WordPress, Shopify och
WooCommerce ingår i alla planer. Planen kontrolleras på servern, inte bara i gränssnittet.

Bot-taket enforce:as av en databas-trigger, konversationstaket och trial-utgången av `/api/chat`
och kanalerna (gemensam policy i `src/lib/ownerPlan.js`).
Priserna anges "exkl. moms" och villkoren säger att moms tillkommer. Stripe Tax är ännu inte
aktiverat, så Checkout lägger inte på någon moms än: aktivera Stripe Tax, sätt prisernas
skattebeteende till "exclusive" och sätt sedan `STRIPE_AUTOMATIC_TAX=true` (inga riktiga
betalningar innan dess).

### Betalningar: lanseringsspärr

Det finns inget företag/momsnummer än, så inga riktiga betalningar får tas — och med en
**testnyckel** (`sk_test_…`) i produktion skulle vem som helst kunna ”betala” med Stripes publika
testkort (4242 4242 4242 4242) och låsa upp en betalplan, dvs. riktig AI-kostnad för plattformen.
En regel på servern (`src/lib/checkoutGate.js`) avgör om ett köp får startas:

| Nyckel | Var | `STRIPE_CHECKOUT_ENABLED` | Checkout |
|--------|-----|---------------------------|----------|
| `sk_live_…` | överallt | osatt / `true` | **öppen** |
| `sk_test_…` | `next dev`, testerna | osatt / `true` | **öppen** (testkort) |
| `sk_test_…` | produktion¹ | osatt / `true` | **stängd** — öppen bara med `STRIPE_ALLOW_TEST_MODE=1` |
| vilken som helst | överallt | `false` | **stängd** (nödbroms) |
| saknas / okänt format | överallt | — | **stängd** |

¹ `NODE_ENV=production` (Vercels production- och preview-deployments, men också lokal
`next start` — sätt `STRIPE_ALLOW_TEST_MODE=1` i `.env.local` för att testköpa där) eller
`VERCEL_ENV=production`/`preview`.

När köpen är stängda svarar `POST /api/checkout` **503** `{ code: "checkout_closed" }` (före allt
annat — inget Checkout, inget planbyte, inget Stripe-anrop), och appen visar ”Betalning öppnar
snart — under tiden kan du använda gratisperioden” / ”Payments open soon — meanwhile you can use
the free trial” med planknapparna avstängda (Fakturering, Välj plan, `/checkout`). Appen frågar
`GET /api/checkout` → `{ open }` (inga hemligheter). Med testnyckel i produktion svarar också
`/api/checkout/verify` och `/api/portal` 503 — en testbetalning ska aldrig låsa upp något där;
nödbromsen stänger däremot inte dem (betalande kunder ska alltid kunna få planen bekräftad och
säga upp). Webhooken ignorerar signerade event vars `livemode` inte matchar nyckelns läge (loggas,
200 så att Stripe inte försöker igen, ingen plan ändras, inget markeras i
`processed_webhook_events`). Adminpanelen visar läget (test/live), om köpen är öppna och vad som
ska sättas (kortet ”Betalningar (Stripe)”).

**Lansering, i den här ordningen:** företag → momsregistrering → Stripe i live-läge
(`STRIPE_SECRET_KEY=sk_live_…`, live-priserna `STRIPE_PRICE_*`, live-endpointens
`STRIPE_WEBHOOK_SECRET`) + Stripe Tax (priserna ”exclusive”) → `STRIPE_AUTOMATIC_TAX=true` →
redeploy. Med live-nyckeln öppnar köpen av sig själva.

## Säkerhet (status 2026-09-30)

- RLS på alla tabeller; `profiles.is_admin/email/id/created_at` skyddade av trigger
- Stripe-webhook: signaturverifierad (fail-closed), idempotent via `processed_webhook_events`,
  ignorerar event från fel läge (test ↔ live)
- Lanseringsspärr för betalningar: testnyckel i produktion = inga köp (`src/lib/checkoutGate.js`)
- Inga lösenord i repot: seed-skripten (`scripts/seed-*.mjs`) tar `SEED_PASSWORD` eller slumpar ett
  starkt lösenord som visas en gång, och vägrar köra mot projektets (produktions-)Supabase utan
  `--i-know-this-is-production`
- SSRF-skydd (värdebaserad IPv4/IPv6-kontroll) på crawl, integrationer och utgående webhooks —
  adresserna kontrolleras även när anslutningen öppnas (skydd mot DNS-rebinding)
- Integrationernas hemligheter krypteras (AES-GCM, `INTEGRATIONS_ENC_KEY`); webbläsaren ser bara
  de sista tecknen. Inkommande kanalmeddelanden verifieras (Telegrams secret_token, Metas signatur)
  och dedupliceras; planen kontrolleras på servern vid varje leverans, kanalsvar och LiveChat-knapp
- Admin avgörs server-side från sessionen — aldrig från klienten
- Hemligheter enbart server-side; publika endpoints rate-limitade per IP och per bot
- `/api/ai` och `/api/crawl` kräver inloggning (verifierad session eller Bearer-token) och har
  rate-limit per användare utöver per IP; `/api/ai` tar bara plattformens egna modeller
- Sidorna kan inte ramas in av andra sajter (`X-Frame-Options: DENY` + CSP `frame-ancestors 'none'`),
  utom `/chat`, `/widget.js` och API:t (`next.config.js`)
- Öppet: rate-limit-store är in-memory (nollställs vid cold start), ingen per-användar-tokenkvot ännu;
  RLS låter ägaren tekniskt skriva sin egen `bots.config` (även `integrations`) direkt mot Supabase —
  appen gör det aldrig och servern validerar värdar/SSRF och plan igen vid användning (ADR-012)

## Admin

Adminpanelen visas för konton med `profiles.is_admin = true` (sätts med service-rollen) eller
med adminadressen (`ADMIN_EMAIL`, bara server-side i `src/lib/adminEmail.js` — appen frågar
`GET /api/admin/me`, så adressen finns aldrig i webbläsarens JavaScript). Se `TASKS.md` för vad som återstår och
`DECISIONS.md` för besluten bakom nuläget.
