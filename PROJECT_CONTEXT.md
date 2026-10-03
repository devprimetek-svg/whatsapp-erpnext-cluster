# PROJECT_CONTEXT.md — WhatsApp Routing + ERPNext CRM Cluster

> How to use: put this file in the project root, open the folder in Antigravity, and start in **Planning mode**.
> Paste one "Prompt" block at a time (Milestone 1 → 4). Approve the plan, let the agent build, then test before moving on.

---

## 1. Goal

Build a decoupled, multi-language WhatsApp support pipeline:

- Customers enter through an **official Meta Cloud API number** (Number 01).
- The actual conversation runs on **swappable Evolution API numbers** (Number 02 / 03) at zero message cost.
- **n8n** orchestrates everything. **ERPNext CRM** stores leads and chat timeline.
- Customers can chat in **Tamil**; agents always write/read **English**. Translation is automatic.

## 2. Architecture

```
Customer (WhatsApp)
   |                         \
   v                          v
Number 01                  Number 02 / 03
(Meta Cloud API)           (Evolution API, GCP)
   |                          ^   ^
   | webhook                  |   | Evolution Manager UI (QR, add numbers)
   v                          v
              n8n  (GCP, Docker)  <----->  Translation AI (GCP Translate / Vertex Gemini Flash)
                |
                v
          ERPNext CRM  (Lead, Communication)
```

**Roles**
- Number 01: entry point, language-selection buttons, system OTPs only.
- Number 02/03: conversational engine, human-agent handoff, translated chat.
- n8n: routing, lead lookup/creation, translation calls, handoff trigger.
- ERPNext: source of truth for Lead + language preference + chat timeline.

## 3. Customer flow ("Proactive Wave")

1. Customer sends "Hi" to Number 01 -> Meta webhook -> n8n.
2. n8n looks up Lead in ERPNext (`/api/resource/Lead`); creates one if missing.
3. Number 01 sends interactive buttons: `English` / `தமிழ் (Tamil)`.
4. On tap: n8n saves language on the Lead (`custom_preferred_language`) and Number 01 says: "Connecting you with our support desk in a new window."
5. n8n immediately calls Evolution API `/message/sendText` so **Number 02 proactively sends the opening greeting** in the chosen language.

## 4. Translation flow

- **Inbound (customer -> agent):** if text contains Tamil characters, n8n translates to English (GCP Translation API or Vertex AI Gemini Flash) and writes both original + translation into ERPNext `Communication`:
  ```
  [Original Tamil]: ...
  [AI English Translation]: ...
  ```
- **Outbound (agent -> customer):** agent writes English in ERPNext -> ERPNext webhook -> n8n checks Lead language -> translates to Tamil -> sends via Evolution API.

## 5. Mandatory non-technical management requirements

- **No hardcoded phone numbers, session IDs, or tokens** in code or workflows.
- Install **Evolution Manager** (web UI) so non-technical managers can create instances, view QR codes, and link new devices (Number 03 etc.) from a browser.
- Active operational number/session must come from one n8n variable: `GLOBAL_OPERATIONAL_WA_NO`. If a number gets banned, admin changes this one value and the whole pipeline switches.

## 6. Tech stack

| Part | Choice |
|---|---|
| Host | GCP VM, Ubuntu 22.04, e2-standard-2 |
| Containers | Docker Compose |
| WhatsApp (official) | Meta WhatsApp Cloud API |
| WhatsApp (swappable) | Evolution API v2 + Evolution Manager |
| Automation | n8n |
| CRM | ERPNext (Frappe) — Lead, Communication, Server Script |
| Translation | GCP Translation API / Vertex AI Gemini Flash |
| SSL | Let's Encrypt (via Caddy reverse proxy) |
| Timezone | Asia/Kolkata |

Domains (replace with real ones): `wa-gateway.yourdomain.com` (Evolution API), `n8n.yourdomain.com` (n8n).

## 7. Known issues in the original dossier — fix these, do not copy blindly

1. **Compose file was incomplete.** Evolution API v2 needs a database (Postgres) and Redis cache; there was also no reverse proxy for SSL. Add Postgres, Redis, and Caddy.
2. **Image name:** dossier says `atendare/evolution-api:v2.1.1`. This is probably a typo. Verify the correct, currently maintained Evolution API v2 image/tag from the official docs/repo before using it.
3. **Evolution Manager:** check the official docs on whether the Manager UI is bundled with the API (served on a `/manager` path) or needs a separate container, and set it up the correct way.
4. **ERPNext server script:** dossier calls `frappe.integrations.offsite__messaging.send_webhook`. This function likely does not exist. Use a supported approach (a Webhook DocType on Communication after insert, or `frappe.make_post_request` inside a Server Script) and verify what is allowed in Server Script sandbox for the installed ERPNext version.
5. **Do not expose ports 8080 / 5678 publicly.** Only Caddy's 80/443 should be public.
6. **Ban risk:** Evolution API is unofficial. Keep the number-swap mechanism working and avoid sending bulk or cold messages from Number 02/03.

## 8. Manual steps (agent cannot do these — document them in README)

- Create/verify Meta Business account; register Number 01 on WhatsApp Cloud API; get permanent access token.
- Get Meta message templates approved (if needed).
- Create DNS A records for the two subdomains pointing to the VM's static IP.
- Scan QR code in Evolution Manager to link Number 02 / 03.
- Create the ERPNext API key/secret for n8n and the custom field `custom_preferred_language` on Lead (if not created by script).

## 9. Working rules for the agent

- Never hardcode secrets. Use `.env` and n8n credentials. Provide `.env.example`.
- Show an implementation plan before writing files; keep each milestone small and testable.
- After each milestone, write short **test steps** (curl commands / sample payloads) in `docs/TESTING.md`.
- Where official docs disagree with this file, trust official docs and tell me what changed.
- Explain anything non-obvious in simple language; I am not a DevOps expert.

---

# PROMPTS — paste one at a time

## Prompt 1 — Milestone 1: Server and containers

```
Read PROJECT_CONTEXT.md fully, especially section 7 (known issues).

Build Milestone 1:
1. docker-compose.yml with: Evolution API v2 (+ Evolution Manager the correct way), n8n,
   Postgres, Redis, and Caddy as reverse proxy with automatic Let's Encrypt SSL.
   - wa-gateway.yourdomain.com -> Evolution API
   - n8n.yourdomain.com -> n8n
   - Only ports 80 and 443 public. All other services on an internal Docker network.
   - Persistent volumes for Evolution instances, Postgres, Redis, n8n, Caddy.
   - restart: always on every service.
2. .env.example with every secret/variable (API key, DB password, domains, timezone Asia/Kolkata,
   n8n encryption key, GLOBAL_OPERATIONAL_WA_NO placeholder). Compose must read from .env.
3. Caddyfile.
4. README.md: step-by-step GCP VM deployment (firewall rules for 80/443, Docker install,
   DNS records, first start, how to open Evolution Manager and scan a QR code).
5. Verify the Evolution API image/tag and required env vars against official docs and tell me
   what you corrected from the original dossier.

Do not run anything on my machine that needs real secrets. Show the plan first.
```

## Prompt 2 — Milestone 2: Meta webhook -> ERPNext Lead

```
Build Milestone 2 as an importable n8n workflow JSON in /n8n/01-inbound-lead.json:
- Webhook node for the Meta WhatsApp Cloud API (include the GET verification handshake
  with verify token, and the POST message receiver).
- Extract sender phone + message text.
- Search ERPNext Lead via /api/resource/Lead (filter by phone/mobile).
- If not found, create a new Lead.
- ERPNext URL and API key/secret come from n8n credentials, never hardcoded.
Also write docs/TESTING.md steps with a sample Meta webhook payload I can POST with curl.
List any ERPNext fields I must create first.
```

## Prompt 3 — Milestone 3: Language selection and Proactive Wave

```
Build Milestone 3 as /n8n/02-language-and-handoff.json:
- From Number 01 (Meta Cloud API) send an interactive reply-button message: English / தமிழ் (Tamil).
- On button reply: save language to the Lead field custom_preferred_language in ERPNext.
- Number 01 then sends: "Connecting you with our support desk in a new window."
- Immediately call Evolution API POST /message/sendText so the active operational number
  sends the opening greeting in the chosen language (English and Tamil text).
- The operational number/instance name must come from the n8n variable GLOBAL_OPERATIONAL_WA_NO.
  No phone numbers or instance names hardcoded in nodes.
Add test steps to docs/TESTING.md. Explain how an admin swaps the number after a ban.
```

## Prompt 4 — Milestone 4: Translation and ERPNext timeline

```
Build Milestone 4:
1. /n8n/03-inbound-translation.json: messages arriving on the Evolution API number ->
   if Tamil characters detected, translate to English (GCP Translation API; mention
   Vertex AI Gemini Flash as alternative) -> create ERPNext Communication with both
   "[Original Tamil]" and "[AI English Translation]" lines.
2. /n8n/04-outbound-translation.json: webhook called by ERPNext when an agent sends a chat
   message -> read Lead language -> translate English to that language -> send via
   Evolution API sendText.
3. /erpnext/: instructions + code for the custom field custom_preferred_language on Lead and
   the outbound trigger on Communication (After Insert). Use a supported ERPNext mechanism
   (see section 7, item 4) and tell me which one you chose and why.
4. Keep GCP credentials out of the repo; document required IAM role and API to enable.
Add end-to-end test steps to docs/TESTING.md.
```
