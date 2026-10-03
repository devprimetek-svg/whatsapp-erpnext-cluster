# ERPNext CRM Setup Guide for WhatsApp Cluster

This guide explains how to configure ERPNext to store WhatsApp leads, track customer language preferences (`English` / `Tamil`), and authenticate n8n REST API calls.

---

## 1. Create the Custom Field on `Lead`

ERPNext needs a custom field to store each customer's language preference.

### Via ERPNext Web UI:
1. Log in to ERPNext as an **Administrator** or user with `System Manager` role.
2. In the Awesomebar (Search bar at top), type **Custom Field List** and press Enter.
3. Click **Add Custom Field** (top right).
4. Fill in the following exact details:
   - **Document (dt)**: `Lead`
   - **Label**: `Preferred Language`
   - **Fieldname**: `custom_preferred_language` *(auto-filled or type manually)*
   - **Field Type**: `Select`
   - **Options**:
     ```text
     Not Set
     English
     Tamil
     ```
   - **Insert After**: `mobile_no` (or `phone`)
   - **Default Value**: `Not Set`
5. Click **Save**.

*(Note: In ERPNext, custom fields created via Custom Field DocType are automatically prefixed with `custom_`, matching `custom_preferred_language`).*

---

## 2. Create an Integration User & Generate API Keys

Never use the `Administrator` account in automated workflows. Create a dedicated API user:

1. Search for **User List** -> click **Add User**.
2. **Email**: `wa_integration@yourdomain.com` (or any valid internal email).
3. **First Name**: `WhatsApp Integration`.
4. **User Type**: `System User`.
5. Under **Roles**, check:
   - `Sales User` (grants read/write permissions on `Lead`)
   - `Customer Service User` or `Support User` (grants permissions on `Communication`)
6. Click **Save**.
7. Scroll down to the **API Access** section on the User form:
   - Click **Generate Keys**.
   - A popup will show the **API Secret**. **Copy this immediately!** It is only shown once.
   - Note the **API Key** displayed on the field.

---

## 3. Configuring Credentials in n8n

In n8n, create two generic credentials:

### Credential 1: ERPNext API Header Auth
- In n8n, navigate to **Credentials** -> **Add Credential** -> Select **Header Auth**.
- **Credential Name**: `ERPNext API Credentials`
- **Name**: `Authorization`
- **Value**: `token YOUR_API_KEY:YOUR_API_SECRET`
  *(Example: `token a1b2c3d4e5:f6g7h8i9j0`)*

### Credential 2: Evolution API Key Header Auth
- In n8n, navigate to **Credentials** -> **Add Credential** -> Select **Header Auth**.
- **Credential Name**: `Evolution API Key Header`
- **Name**: `apikey`
- **Value**: *(The `AUTHENTICATION_API_KEY` defined in your `.env` file)*

---

## 4. Test ERPNext REST API Connection via Curl

Run this command from your terminal to verify that your API key works and the Lead endpoint responds:

```bash
export ERPNEXT_URL="https://erp.yourdomain.com"
export API_KEY="your_erpnext_api_key"
export API_SECRET="your_erpnext_api_secret"

# Test 1: Fetch existing leads
curl -s -X GET "$ERPNEXT_URL/api/resource/Lead?limit=1" \
  -H "Authorization: token $API_KEY:$API_SECRET" \
  -H "Content-Type: application/json"

# Test 2: Verify custom field is active
curl -s -X GET "$ERPNEXT_URL/api/resource/Custom%20Field/Lead-custom_preferred_language" \
  -H "Authorization: token $API_KEY:$API_SECRET"
```

**Expected Result**: Both commands return HTTP 200 with JSON data.

---

## 5. Setting up Outbound WhatsApp Trigger (Agent -> Customer)

When an agent replies to a Lead in ERPNext, we must automatically trigger n8n (`/webhook/erpnext-outbound`) to translate the message and dispatch it to the customer via WhatsApp.

### Technical Decision: Why Webhook DocType Over Server Script
In the original project dossier, the script attempted to call `frappe.integrations.offsite__messaging.send_webhook`. **That function does not exist in standard Frappe.**

We evaluated the two real supported mechanisms:
1. **Frappe Native Webhook DocType (Chosen & Recommended)**:
   - Built directly into Frappe/ERPNext core.
   - Handled asynchronously via Frappe Redis worker queue (`frappe.enqueue`), ensuring the agent's browser interface never lags during WhatsApp/Translation API calls.
   - Requires zero Python code and bypasses the `safe_exec` security restrictions that often block network calls in Server Scripts.
2. **Server Script (`frappe.make_post_request`) (Supported Alternative)**:
   - Only works if `server_script_enabled: true` is configured in `site_config.json`. We provided the complete script in [`server_script_outbound.py`](file:///C:/Users/Dawood/.gemini/antigravity/scratch/whatsapp-erpnext-cluster/erpnext/server_script_outbound.py) if your deployment mandates it.

---

### Step-by-Step Configuration: Webhook DocType

1. In ERPNext search bar, type **Webhook List** and press Enter.
2. Click **Add Webhook**.
3. Fill in the following settings:
   - **DocType**: `Communication`
   - **Webhook Doctype Event**: `after_insert`
   - **Request URL**: `https://n8n.yourdomain.com/webhook/erpnext-outbound`
   - **Request Method**: `POST`
   - **Condition**:
     ```python
     doc.reference_doctype == "Lead" and doc.sent_or_received == "Sent" and doc.communication_medium == "WhatsApp"
     ```
   - **Webhook Headers**:
     - Key: `Content-Type`, Value: `application/json`
   - **Webhook Data**:
     Select **Send Document Data** (or add key-value pairs for `name`, `reference_doctype`, `reference_name`, `content`, `sent_or_received`, `sender`).
4. Click **Save**.

---

### How Agents Send a WhatsApp Reply in ERPNext
1. Open any **Lead** record in ERPNext CRM.
2. In the timeline at the bottom, click **New Email / Communication** (or Add Comment).
3. Set:
   - **Communication Medium**: `WhatsApp`
   - **Sent or Received**: `Sent`
4. Type your reply in standard **English** (e.g., *"Hello! We have reviewed your documents and approved your request."*).
5. Click **Save / Send**.
6. ERPNext fires the webhook -> n8n checks the Lead language -> translates to Tamil -> delivers to customer's WhatsApp in seconds!
