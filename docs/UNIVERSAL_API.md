# Universal WhatsApp Gateway REST API Documentation

This API allows any external web application (Next.js, React, Node.js, Python, Laravel, Flutter, etc.) to send WhatsApp messages, trigger automated Tamil-English translations, and receive inbound customer messages through your self-hosted cluster.

---

## 1. Quick Overview

- **Base URL**: `https://n8n.yourdomain.com`
- **Outbound Endpoint**: `POST /webhook/api/v1/send-message`
- **Authentication**: Custom HTTP Header `x-api-key: <YOUR_UNIVERSAL_GATEWAY_API_KEY>`
- **Content-Type**: `application/json`

---

## 2. Authentication

Every request to the Universal API must include the header:

```http
x-api-key: your_configured_gateway_api_key
```

Define this key in your server's `.env` file under `UNIVERSAL_GATEWAY_API_KEY`.

---

## 3. Outbound Message API

### Request Specification
`POST https://n8n.yourdomain.com/webhook/api/v1/send-message`

#### Headers
| Header | Type | Required | Description |
|---|---|---|---|
| `x-api-key` | string | **Yes** | Master gateway authentication key |
| `Content-Type` | string | **Yes** | `application/json` |

#### Request Body
| Field | Type | Required | Description |
|---|---|---|---|
| `to` | string | **Yes** | Customer phone number with country code (e.g. `"919876543210"`). Whitespace and symbols are stripped automatically. |
| `message` | string | **Yes** | Message body to deliver. |
| `target_language` | string | No | Language translation mode: <br/>• `"tamil"` or `"ta"`: Automatically translates English text into Tamil before sending. <br/>• `"original"` *(default)*: Sends message text exactly as written. |
| `source` | string | No | Tag identifying calling application (e.g. `"ecommerce_web"`, `"billing_portal"`). |
| `metadata` | object | No | Custom JSON payload for tracking (e.g. `{"order_id": 9948, "user_id": 412}`). |

---

### Example Request Payloads

#### Example A: Send Direct Notification (English / As-is)
```json
{
  "to": "919876543210",
  "message": "Your one-time login OTP is 482910. Valid for 5 minutes.",
  "source": "auth_service"
}
```

#### Example B: Send Message with Auto-Translation to Tamil
```json
{
  "to": "919876543210",
  "message": "Hello Karthik, your order #9948 has been shipped and will be delivered tomorrow.",
  "target_language": "tamil",
  "source": "storefront",
  "metadata": {
    "order_id": "9948"
  }
}
```
*The customer receives on WhatsApp*:
> "வணக்கம் கார்த்திக், உங்கள் ஆர்டர் #9948 அனுப்பப்பட்டுவிட்டது மற்றும் நாளை வந்து சேரும்."

---

### Response Specification

#### Success Response (HTTP 200 OK)
```json
{
  "success": true,
  "status": "dispatched",
  "recipient": "919876543210",
  "dispatched_text": "Delivered",
  "translated": true,
  "instance": "support_primary",
  "timestamp": 1727941200
}
```

#### Error Responses
- **HTTP 401 Unauthorized**:
  ```json
  { "success": false, "error": "Unauthorized: Invalid or missing x-api-key header" }
  ```
- **HTTP 400 Bad Request**:
  ```json
  { "success": false, "error": "Bad Request: \"to\" and \"message\" fields are required" }
  ```

---

## 4. Code Integration Snippets for Developers

### cURL
```bash
curl -X POST "https://n8n.yourdomain.com/webhook/api/v1/send-message" \
  -H "x-api-key: your_configured_gateway_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "919876543210",
    "message": "Your payment has been successfully received.",
    "target_language": "tamil"
  }'
```

---

### Node.js / JavaScript (Fetch API)
```javascript
async function sendWhatsAppAlert(phoneNumber, messageText, autoTranslate = false) {
  const GATEWAY_URL = 'https://n8n.yourdomain.com/webhook/api/v1/send-message';
  const API_KEY = process.env.WHATSAPP_GATEWAY_KEY;

  const response = await fetch(GATEWAY_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY
    },
    body: JSON.stringify({
      to: phoneNumber,
      message: messageText,
      target_language: autoTranslate ? 'tamil' : 'original',
      source: 'nodejs_app'
    })
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to dispatch WhatsApp message');
  }
  return data;
}

// Example usage:
sendWhatsAppAlert('919876543210', 'Welcome to our platform!', true)
  .then(res => console.log('WhatsApp sent:', res))
  .catch(err => console.error('Error:', err));
```

---

### Python (Requests)
```python
import os
import requests

def send_whatsapp(to_number: str, message: str, translate_tamil: bool = False):
    url = "https://n8n.yourdomain.com/webhook/api/v1/send-message"
    headers = {
        "x-api-key": os.getenv("WHATSAPP_GATEWAY_KEY"),
        "Content-Type": "application/json"
    }
    payload = {
        "to": to_number,
        "message": message,
        "target_language": "tamil" if translate_tamil else "original",
        "source": "python_backend"
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

# Example usage:
result = send_whatsapp("919876543210", "Your appointment is confirmed for tomorrow 10 AM.", translate_tamil=True)
print(result)
```

---

### Next.js (Server Action / Route Handler)
```typescript
// app/api/notify/route.ts
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const { phone, customerName, orderId } = await req.json();

  const res = await fetch('https://n8n.yourdomain.com/webhook/api/v1/send-message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': process.env.WHATSAPP_GATEWAY_KEY!
    },
    body: JSON.stringify({
      to: phone,
      message: `Hello ${customerName}, your order #${orderId} is confirmed!`,
      target_language: 'tamil',
      source: 'nextjs_storefront'
    })
  });

  const result = await res.json();
  return NextResponse.json(result, { status: res.status });
}
```

---

## 5. Inbound Webhook: Forwarding Messages to Your Web App

When customers send messages to your WhatsApp number, you can configure n8n to notify your web app in real time:

### Webhook Event Sent to Your Web App
`POST https://your-webapp.com/api/webhooks/whatsapp`

```json
{
  "event": "whatsapp.message.received",
  "from": "919876543210",
  "sender_name": "Karthik Subramanian",
  "original_message": "வணக்கம், எனது ஆர்டர் நிலையை சரிபார்க்க விரும்புகிறேன்",
  "translated_message": "Hello, I would like to check my order status",
  "detected_language": "Tamil",
  "timestamp": 1727939100
}
```
*(Both ERPNext and your Web App receive the data simultaneously, keeping your CRM and custom application in perfect sync).*
