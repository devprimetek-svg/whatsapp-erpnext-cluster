# Cluster Verification & Testing Runbook

This document details verification tests for each milestone of the WhatsApp Routing + ERPNext CRM cluster.

---

## Milestone 1: Server and Container Infrastructure Verification

Run these commands either from your local terminal or directly inside the VM to verify connectivity, SSL provisioning, and service health.

### 1. Pre-requisite Shell Variables
For testing, export your target domains and API key in your terminal:

```bash
export WA_GATEWAY="https://wa-gateway.yourdomain.com"
export WA_MANAGER="https://wa-manager.yourdomain.com"
export N8N_URL="https://n8n.yourdomain.com"
export EVO_API_KEY="your_configured_authentication_api_key"
```

---

### 2. Service Verification Tests

#### Test 1.1: Caddy SSL Certificate & Reverse Proxy Inspection
Verify that Caddy has successfully obtained a Let's Encrypt TLS certificate for each domain:

```bash
# Verify Evolution API Gateway SSL
curl -Iv $WA_GATEWAY 2>&1 | grep -E "SSL certificate verify ok|HTTP/2 200|HTTP/1.1 200"

# Verify n8n SSL
curl -Iv $N8N_URL 2>&1 | grep -E "SSL certificate verify ok|HTTP/2 200|HTTP/1.1 200"

# Verify Evolution Manager SSL
curl -Iv $WA_MANAGER 2>&1 | grep -E "SSL certificate verify ok|HTTP/2 200|HTTP/1.1 200"
```

**Expected Result**: All output lines should return `SSL certificate verify ok` and HTTP `200` or `302`.

---

#### Test 1.2: Evolution API Gateway Health & Root
Query the root status endpoint of Evolution API v2:

```bash
curl -s -X GET "$WA_GATEWAY/"
```

**Expected Response**:
```json
{
  "status": 200,
  "message": "Welcome to the Evolution API",
  "version": "2.2.2"
}
```

---

#### Test 1.3: Evolution API Authentication & Database Connectivity
Query the instance list using the master API key in the `apikey` header:

```bash
curl -s -X GET "$WA_GATEWAY/instance/fetchInstances" \
  -H "apikey: $EVO_API_KEY" \
  -H "Content-Type: application/json"
```

**Expected Response**:
```json
[]
```
*(Returns an empty JSON array if no instances have been created yet, confirming successful PostgreSQL connection and authentication).*

---

#### Test 1.4: Evolution Manager Web Interface
Check that the Evolution Manager frontend returns HTTP 200 and serves HTML:

```bash
curl -s -I "$WA_MANAGER" | head -n 5
```

**Expected Response**:
```http
HTTP/2 200
content-type: text/html; charset=utf-8
```

---

#### Test 1.5: n8n Orchestrator Health Endpoint
Check n8n's built-in health endpoint:

```bash
curl -s -I "$N8N_URL/healthz"
```

**Expected Response**:
```http
HTTP/2 200
content-type: application/json; charset=utf-8
```

---

### 3. Docker Container Health & Logs Inspection (On VM)

If any test fails, run the following commands on the GCP VM to diagnose:

```bash
# Check status of all containers (notice (healthy) next to postgres and redis)
docker compose ps

# Check Caddy certificate issuance logs
docker compose logs -f caddy

# Check Evolution API backend logs (verify PostgreSQL and Redis connections)
docker compose logs -f evolution_api

# Check n8n startup logs
docker compose logs -f n8n
```

---

## Milestone 2: WhatsApp Webhook & ERPNext Lead Pipeline Testing

These tests allow you to simulate inbound WhatsApp messages using `curl` without needing a live phone or Meta developer account.

### 1. Pre-requisites
Ensure the workflow `01 - Direct WhatsApp Inbound to ERPNext Lead` is imported and **Active** in n8n.

Export the test parameters in your shell:
```bash
export N8N_WEBHOOK="https://n8n.yourdomain.com/webhook/evolution-inbound"
export ERPNEXT_URL="https://erp.yourdomain.com"
export API_KEY="your_erpnext_api_key"
export API_SECRET="your_erpnext_api_secret"
```
*(If running against the n8n test canvas, use `/webhook-test/evolution-inbound` instead).*

---

### 2. Verification Tests

#### Test 2.1: Simulate New Customer Message ("Hi") via Evolution Webhook
Send a simulated Baileys `messages.upsert` payload from a new customer phone (`919876543210`):

```bash
curl -s -X POST "$N8N_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "support_primary",
    "data": {
      "key": {
        "remoteJid": "919876543210@s.whatsapp.net",
        "fromMe": false,
        "id": "SIMULATED_MSG_001"
      },
      "pushName": "Karthik Subramanian",
      "message": {
        "conversation": "Hi, I need assistance with your service."
      },
      "messageType": "conversation",
      "messageTimestamp": 1727938800
    }
  }'
```

**Expected Workflow Actions**:
1. Filter passes (`fromMe: false`, valid mobile `919876543210`).
2. Search query to ERPNext returns `data: []` (Lead does not exist).
3. n8n creates a new Lead in ERPNext with `lead_name: "Karthik Subramanian"` and `mobile_no: "919876543210"`.
4. n8n triggers Evolution API to send the Language Selection Menu:
   > "Welcome to Support! 👋  
   > Please select your preferred language:  
   > 1️⃣ Reply *1* for English  
   > 2️⃣ தமிழ் மொழிக்கு *2* என பதிலளிக்கவும்"

---

#### Test 2.2: Verify Lead Creation in ERPNext
Query ERPNext via curl to confirm the Lead was created:

```bash
curl -s -X GET "$ERPNEXT_URL/api/resource/Lead?filters=[[\"mobile_no\",\"like\",\"%919876543210%\"]]&fields=[\"name\",\"lead_name\",\"mobile_no\",\"custom_preferred_language\",\"source\"]" \
  -H "Authorization: token $API_KEY:$API_SECRET"
```

**Expected Response**:
```json
{
  "data": [
    {
      "name": "CRM-LEAD-2026-00001",
      "lead_name": "Karthik Subramanian",
      "mobile_no": "919876543210",
      "custom_preferred_language": "Not Set",
      "source": "WhatsApp"
    }
  ]
}
```

---

#### Test 2.3: Simulate Customer Selecting Language ("2" for Tamil)
Send a second message where the customer replies with `2`:

```bash
curl -s -X POST "$N8N_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "support_primary",
    "data": {
      "key": {
        "remoteJid": "919876543210@s.whatsapp.net",
        "fromMe": false,
        "id": "SIMULATED_MSG_002"
      },
      "pushName": "Karthik Subramanian",
      "message": {
        "conversation": "2"
      },
      "messageType": "conversation",
      "messageTimestamp": 1727938830
    }
  }'
```

**Expected Workflow Actions**:
1. n8n searches ERPNext and finds existing Lead `CRM-LEAD-2026-00001`.
2. Detects input `2` -> Maps to language `Tamil`.
3. Updates `custom_preferred_language` on the Lead to `Tamil`.
4. Dispatches the Tamil confirmation message via Evolution API:
   > "நன்றி! உங்கள் விருப்ப மொழி தமிழ் என பதிவு செய்யப்பட்டுள்ளது. எங்கள் ஆதரவு குழு உங்களுக்கு உதவ தயாராக உள்ளது. உங்கள் கேள்வியை பகிரவும்."

---

#### Test 2.4: Verify Language Update on the Lead
Verify the Lead in ERPNext now shows `Tamil`:

```bash
curl -s -X GET "$ERPNEXT_URL/api/resource/Lead?filters=[[\"mobile_no\",\"like\",\"%919876543210%\"]]&fields=[\"name\",\"custom_preferred_language\"]" \
  -H "Authorization: token $API_KEY:$API_SECRET"
```

**Expected Response**:
```json
{
  "data": [
    {
      "name": "CRM-LEAD-2026-00001",
      "custom_preferred_language": "Tamil"
    }
  ]
}
```

---

#### Test 2.5: Simulated Meta Cloud API Webhook (Future Reference)
If you import `/n8n/01-meta-inbound-lead.json` when connecting Meta Cloud API:

**Step 1: Test GET Verification Handshake**:
```bash
curl -s -X GET "https://n8n.yourdomain.com/webhook/meta-wa-webhook?hub.mode=subscribe&hub.challenge=11559988&hub.verify_token=my_secure_meta_token_123"
```
*Expected Response*: `11559988` (Status HTTP 200).

**Step 2: Test Inbound POST Message**:
```bash
curl -s -X POST "https://n8n.yourdomain.com/webhook/meta-wa-webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "metadata": {
            "display_phone_number": "15550234567",
            "phone_number_id": "PHONE_NUMBER_ID"
          },
          "contacts": [{
            "profile": { "name": "Priya Raman" },
            "wa_id": "919123456780"
          }],
          "messages": [{
            "from": "919123456780",
            "id": "wamid.HBgLMTE1NT...",
            "timestamp": "1727938900",
            "text": { "body": "வணக்கம்" },
            "type": "text"
          }]
        },
        "field": "messages"
      }]
    }]
  }'
```

---

## Milestone 3 & Milestone 4: Translation & CRM Timeline Verification

These tests verify the end-to-end bi-directional translation (Tamil <-> English), ERPNext Communication history synchronization, and operational number swapping.

### 1. Pre-requisites
Ensure the following workflows are imported and **Active** in n8n:
- `03 - Inbound WhatsApp Translation to ERPNext Communication`
- `04 - Outbound ERPNext Agent Chat Translation to WhatsApp`
- `02 - Meta Interactive Language & Proactive Wave Handoff` *(if testing Meta)*

Export your test variables:
```bash
export N8N_INBOUND_CHAT="https://n8n.yourdomain.com/webhook/evolution-inbound-chat"
export N8N_OUTBOUND="https://n8n.yourdomain.com/webhook/erpnext-outbound"
export ERPNEXT_URL="https://erp.yourdomain.com"
export API_KEY="your_erpnext_api_key"
export API_SECRET="your_erpnext_api_secret"
```

---

### 2. Inbound Translation Verification (Customer Tamil -> Agent English)

#### Test 4.1: Simulate Customer Sending Message in Tamil
Send a simulated WhatsApp message with genuine Tamil characters from customer `919876543210`:

```bash
curl -s -X POST "$N8N_INBOUND_CHAT" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "support_primary",
    "data": {
      "key": {
        "remoteJid": "919876543210@s.whatsapp.net",
        "fromMe": false,
        "id": "TAMIL_MSG_001"
      },
      "pushName": "Karthik Subramanian",
      "message": {
        "conversation": "வணக்கம், எனது ஆர்டர் நிலையை சரிபார்க்க விரும்புகிறேன்"
      },
      "messageType": "conversation",
      "messageTimestamp": 1727939100
    }
  }'
```

**Expected Workflow Processing**:
1. Unicode Regex `[\u0B80-\u0BFF]` detects Tamil script (`isTamil: true`).
2. GCP Translation API translates `"வணக்கம், எனது ஆர்டர் நிலையை சரிபார்க்க விரும்புகிறேன்"` -> `"Hello, I would like to check my order status"`.
3. n8n searches ERPNext for Lead matching phone `919876543210`.
4. Creates a new `Communication` record linked to the Lead.

---

#### Test 4.2: Inspect Communication on ERPNext Lead Timeline
Query the `Communication` record created in ERPNext:

```bash
curl -s -X GET "$ERPNEXT_URL/api/resource/Communication?filters=[[\"reference_name\",\"like\",\"%CRM-LEAD-%\"]]&fields=[\"name\",\"reference_name\",\"subject\",\"content\",\"sent_or_received\"]&order_by=creation%20desc&limit=1" \
  -H "Authorization: token $API_KEY:$API_SECRET"
```

**Expected Response**:
```json
{
  "data": [
    {
      "name": "COMM-2026-00001",
      "reference_name": "CRM-LEAD-2026-00001",
      "subject": "WhatsApp Message from 919876543210",
      "content": "[Original Tamil]:<br/>வணக்கம், எனது ஆர்டர் நிலையை சரிபார்க்க விரும்புகிறேன்<br/><br/>[AI English Translation]:<br/>Hello, I would like to check my order status",
      "sent_or_received": "Received"
    }
  ]
}
```

---

### 3. Outbound Translation Verification (Agent English -> Customer Tamil)

#### Test 4.3: Simulate Support Agent Replying in English via ERPNext
Simulate ERPNext Webhook firing when an agent writes an English response on Lead `CRM-LEAD-2026-00001`:

```bash
curl -s -X POST "$N8N_OUTBOUND" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "COMM-2026-00002",
    "reference_doctype": "Lead",
    "reference_name": "CRM-LEAD-2026-00001",
    "sent_or_received": "Sent",
    "content": "<p>Hello Karthik, your order #9948 has been dispatched and will arrive tomorrow.</p>",
    "sender": "support.agent@yourdomain.com"
  }'
```

**Expected Workflow Processing**:
1. Filter verifies `reference_doctype === "Lead"` and `sent_or_received === "Sent"`.
2. Sanitizer extracts clean text: `"Hello Karthik, your order #9948 has been dispatched and will arrive tomorrow."`.
3. Fetches Lead `CRM-LEAD-2026-00001` from ERPNext and inspects `custom_preferred_language` (`Tamil`).
4. GCP Translation API translates the English message to Tamil:
   `"வணக்கம் கார்த்திக், உங்கள் ஆர்டர் #9948 அனுப்பப்பட்டுவிட்டது மற்றும் நாளை வந்து சேரும்."`
5. Dispatches payload to Evolution API:
   `POST /message/sendText/support_primary` with customer's WhatsApp number.

---

### 4. Operational Number Failover Test (Banned Number Recovery)

#### Test 4.4: Verify Zero-Downtime Number Switch
When `GLOBAL_OPERATIONAL_WA_NO` is changed from `support_primary` to `support_secondary`:

1. Update `.env` or n8n variable `GLOBAL_OPERATIONAL_WA_NO=support_secondary`.
2. Trigger the outbound webhook test again:
```bash
curl -s -X POST "$N8N_OUTBOUND" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "COMM-2026-00003",
    "reference_doctype": "Lead",
    "reference_name": "CRM-LEAD-2026-00001",
    "sent_or_received": "Sent",
    "content": "<p>Is there anything else we can assist you with?</p>",
    "sender": "support.agent@yourdomain.com"
  }'
```
3. Inspect n8n execution log:
   - Notice the Evolution API request URL automatically dynamically resolved to:
     `https://wa-gateway.yourdomain.com/message/sendText/support_secondary`
   - Zero workflows modified; failover completed instantly.

---

## Milestone 5: Universal Web App Gateway API Verification

These tests verify that any custom web app (Next.js, React, Node.js, Python, etc.) can send WhatsApp messages and trigger automated translation via the Universal Gateway API.

### 1. Pre-requisites
Ensure workflow `05 - Universal WhatsApp Gateway API` is imported and **Active** in n8n.

Export the test variables:
```bash
export UNIVERSAL_API="https://n8n.yourdomain.com/webhook/api/v1/send-message"
export GATEWAY_KEY="your_configured_universal_gateway_api_key"
```

---

### 2. Universal API Verification Tests

#### Test 5.1: Verify API Key Security (Unauthorized Request)
Attempt to send a message without the `x-api-key` header:

```bash
curl -s -i -X POST "$UNIVERSAL_API" \
  -H "Content-Type: application/json" \
  -d '{"to": "919876543210", "message": "Unauthorized test"}'
```

**Expected Response**:
```http
HTTP/2 401 Unauthorized
```
```json
{
  "success": false,
  "error": "Unauthorized: Invalid or missing x-api-key header"
}
```

---

#### Test 5.2: Send Direct Message from Web App (English)
Send an authenticated message from your custom application:

```bash
curl -s -X POST "$UNIVERSAL_API" \
  -H "x-api-key: $GATEWAY_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "919876543210",
    "message": "Your verification code is 492019. Valid for 10 minutes.",
    "source": "auth_service"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "status": "dispatched",
  "recipient": "919876543210",
  "dispatched_text": "Delivered",
  "translated": false,
  "instance": "support_primary",
  "timestamp": 1727941200
}
```

---

#### Test 5.3: Send Message with Automatic Tamil Translation
Send an English message with `target_language: "tamil"`:

```bash
curl -s -X POST "$UNIVERSAL_API" \
  -H "x-api-key: $GATEWAY_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "919876543210",
    "message": "Hello! Your payment has been received successfully. Thank you for your business.",
    "target_language": "tamil",
    "source": "checkout_app"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "status": "dispatched",
  "recipient": "919876543210",
  "dispatched_text": "Delivered",
  "translated": true,
  "instance": "support_primary",
  "timestamp": 1727941230
}
```
*Customer receives Tamil translation on WhatsApp*:
> "வணக்கம்! உங்கள் கட்டணம் வெற்றிகரமாக பெறப்பட்டது. எங்களுடன் இணைந்தமைக்கு நன்றி."
