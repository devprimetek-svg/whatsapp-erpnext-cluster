# ERPNext CRM Dedicated WhatsApp Pipeline Guide

This guide explains the dedicated, isolated WhatsApp pipeline built specifically for **ERPNext CRM** (Leads, Communication Timeline, and Bi-directional Tamil ↔ English Translation).

---

## 1. Pipeline Overview & Isolation

This pipeline runs completely independently from PRIMETEK. It only touches ERPNext CRM records and communicates exclusively through the dedicated ERPNext WhatsApp support number.

- **Dedicated WhatsApp Instance**: `erpnext_support` (swappable operational number).
- **Dedicated Webhook Endpoints**:
  - `POST /webhook/erpnext/inbound-lead` (New customer entry & Lead creation)
  - `POST /webhook/erpnext/inbound-chat` (Inbound Tamil detection & CRM timeline sync)
  - `POST /webhook/erpnext/outbound-reply` (Agent reply translation & WhatsApp dispatch)
- **CRM DocTypes**: `Lead` and `Communication`

```
Customer sends message to ERPNext WhatsApp Number
                    │
                    ▼
Evolution API (Instance: erpnext_support)
                    │
                    ▼
n8n Cluster (ERPNext Workflows)
   ├── Detects Tamil characters ([\u0B80-\u0BFF])
   ├── Translates to English (GCP Cloud Translation)
   └── Creates Lead / Communication in ERPNext CRM!
```

---

## 2. Setting Up the WhatsApp Instance in Evolution Manager

1. Open Evolution Manager: `https://wa-manager.yourdomain.com`
2. Log in with your cluster's `AUTHENTICATION_API_KEY`.
3. Click **Create Instance**:
   - **Instance Name**: `erpnext_support` *(exact name)*
   - **Integration Type**: `Baileys`
4. Click **Create**.
5. Scan the QR code using WhatsApp on the phone number designated for ERPNext Support.
6. Status will change to **Connected**.

---

## 3. Importing the Workflows into n8n

Open your n8n interface (`https://n8n.yourdomain.com`) and import the 3 workflows from `/n8n/erpnext/`:

1. **`01-erpnext-inbound-lead.json`**: Creates a new Lead in ERPNext when an unknown customer sends a message and prompts for language choice.
2. **`02-erpnext-translation-timeline.json`**: Detects Tamil script in incoming messages, translates to English, and logs a dual-language `Communication` card on the Lead's timeline.
3. **`03-erpnext-agent-outbound.json`**: Listens for agent replies in ERPNext, translates English to Tamil, and delivers via WhatsApp.

Toggle all 3 workflows to **Active**.

---

## 4. ERPNext CRM Configuration Checklist

1. **Custom Field**:
   - DocType: `Custom Field` -> Add for `Lead`.
   - Fieldname: `custom_preferred_language` (Type: `Select`, Options: `Not Set\nEnglish\nTamil`).
2. **API Credentials**:
   - In ERPNext, create an API user (`wa_integration@yourdomain.com`) and generate API Key and Secret.
   - Add these in n8n under generic credential **ERPNext API Credentials**.
3. **Webhook DocType (Agent Outbound Trigger)**:
   - Target DocType: `Communication`
   - Event: `after_insert`
   - URL: `https://n8n.yourdomain.com/webhook/erpnext/outbound-reply`
   - Condition: `doc.reference_doctype == "Lead" and doc.sent_or_received == "Sent" and doc.communication_medium == "WhatsApp"`

---

## 5. Testing the ERPNext Pipeline (cURL)

#### Inbound Tamil Customer Message:
```bash
curl -s -X POST "https://n8n.yourdomain.com/webhook/erpnext/inbound-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "erpnext_support",
    "data": {
      "key": { "remoteJid": "919876543210@s.whatsapp.net", "fromMe": false, "id": "TEST_001" },
      "pushName": "Karthik",
      "message": { "conversation": "வணக்கம், எனக்கு உதவி தேவை" }
    }
  }'
```
*Creates a Lead and logs dual-text translation on the timeline in ERPNext CRM!*
