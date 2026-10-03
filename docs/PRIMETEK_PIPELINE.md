# PRIMETEK Dedicated WhatsApp Pipeline Guide

This guide explains the dedicated, isolated WhatsApp pipeline built specifically for the **PRIMETEK Storefront, Checkout, and Admin Panel** (www.primetek.online).

---

## 1. Pipeline Overview & Isolation

This pipeline runs completely independently from ERPNext. No shopping cart orders or storefront inquiries will ever pollute ERPNext CRM leads unless specifically configured.

- **Dedicated WhatsApp Instance**: `primetek_store` (linked to PRIMETEK's business number `918062181385`).
- **Dedicated Webhook Endpoints**:
  - `POST /webhook/primetek/v1/checkout-order` (Checkout order receipts)
  - `POST /webhook/primetek/v1/admin-message` (Admin CRM & direct dispatch)
  - `POST /webhook/primetek/inbound-chat` (Incoming customer support chats)
- **Authentication**: Custom HTTP Header `x-primetek-key: <PRIMETEK_GATEWAY_API_KEY>`

```
Customer checks out on primetek.online
         │
         ▼
[POST /webhook/primetek/v1/checkout-order]
         │ (x-primetek-key header)
         ▼
n8n Cluster (PRIMETEK Workflow 01)
         │
         ▼
Evolution API (Instance: primetek_store)
         │
         ▼
Customer receives official WhatsApp receipt!
```

---

## 2. Setting Up the WhatsApp Instance in Evolution Manager

1. Open Evolution Manager: `https://wa-manager.yourdomain.com`
2. Log in with your cluster's `AUTHENTICATION_API_KEY`.
3. Click **Create Instance**:
   - **Instance Name**: `primetek_store` *(exact name)*
   - **Integration Type**: `Baileys`
4. Click **Create**.
5. Scan the QR code using WhatsApp on the phone number designated for PRIMETEK (`+91 8062181385`).
6. Status will change to **Connected**.

---

## 3. Importing the Workflows into n8n

Open your n8n interface (`https://n8n.yourdomain.com`) and import the 3 workflows from `/n8n/primetek/`:

1. **`01-primetek-checkout-orders.json`**: Dispatches automated order receipts when customers checkout on `checkout.html`.
2. **`02-primetek-admin-dispatch.json`**: Enables 1-click WhatsApp messaging directly from the Admin CRM Kanban board (`admin.html`).
3. **`03-primetek-inbound-support.json`**: Handles incoming WhatsApp messages from customers and sends automated greetings.

Toggle all 3 workflows to **Active**.

---

## 4. Connecting PRIMETEK Website (`whatsapp-config.js`)

In the `PRIMETEK` repository, open `whatsapp-config.js` and set:

```javascript
window.PRIMETEK_WA_CONFIG = {
  ENABLED: true,
  GATEWAY_URL: 'https://n8n.yourdomain.com/webhook/primetek/v1/checkout-order',
  API_KEY: 'your_primetek_gateway_api_key_from_env',
  DEFAULT_LANGUAGE: 'original'
};
```

---

## 5. Testing the PRIMETEK Pipeline (cURL)

Simulate a customer checkout order to verify the dedicated pipeline:

```bash
curl -X POST "https://n8n.yourdomain.com/webhook/primetek/v1/checkout-order" \
  -H "x-primetek-key: your_primetek_gateway_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Karthik Subramanian",
    "phone": "919876543210",
    "email": "karthik@example.com",
    "summary": "1x Full-Stack Inventory & Billing ERP — ₹15,000",
    "total": 15000,
    "notes": "Need UPI QR code for billing"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "status": "dispatched",
  "service": "PRIMETEK Storefront",
  "recipient": "919876543210",
  "customer": "Karthik Subramanian",
  "instance": "primetek_store"
}
```
