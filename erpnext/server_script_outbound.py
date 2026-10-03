# ==============================================================================
# ERPNext Server Script: Outbound WhatsApp Dispatch Trigger
# ==============================================================================
# Instructions:
# 1. In ERPNext, search for "Server Script List" and click "Add Server Script".
# 2. Set Script Type: "DocType Event"
# 3. Set Reference DocType: "Communication"
# 4. Set DocType Event: "After Insert"
# 5. Paste the code below and Save.
#
# NOTE: If Server Scripts are restricted on your host (server_script_enabled = False),
# use the native ERPNext Webhook DocType instead (recommended). See /erpnext/README.md.
# ==============================================================================

if (
    doc.reference_doctype == "Lead"
    and doc.sent_or_received == "Sent"
    and (doc.communication_medium == "WhatsApp" or getattr(doc, "custom_send_to_whatsapp", False))
):
    # n8n outbound webhook endpoint (replace with your domain or internal docker hostname)
    webhook_url = "https://n8n.yourdomain.com/webhook/erpnext-outbound"

    payload = {
        "name": doc.name,
        "reference_doctype": doc.reference_doctype,
        "reference_name": doc.reference_name,
        "sent_or_received": doc.sent_or_received,
        "content": doc.content,
        "sender": doc.sender,
        "creation": str(doc.creation)
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        # frappe.make_post_request is the official supported method in Frappe
        # (replaces the non-existent frappe.integrations.offsite__messaging.send_webhook)
        frappe.make_post_request(webhook_url, data=payload, headers=headers)
    except Exception as e:
        frappe.log_error(title="WhatsApp Outbound Trigger Error", message=str(e))
