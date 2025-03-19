import frappe
from erpnext import get_default_currency
from frappe import _
from frappe.desk.doctype.number_card.number_card import get_result

def format_number(value: float) -> str:
    """
    Format a number into human-readable format with suffix (K, L, Cr).
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        frappe.log_error(title=_("PWA app"), message=_("Invalid value provided for formatting"))
        return float(0)

    if value >= 10000000:
        return f'{value / 10000000:.1f}Cr'
    elif value >= 100000:
        return f'{value / 100000:.1f}L'
    elif value >= 1000:
        return f'{value / 1000:.1f}K'
    else:
        return float(value)


@frappe.whitelist()
def get_number_card_details(docname: str) -> dict:
    """
    Fetches and formats details for a Number Card based on its configuration.
    
    Args:
        docname (str): Name of the Number Card document.

    Returns:
        dict: Number card details including name, color, and value.
    """
    if not frappe.db.exists("Number Card", docname):
        frappe.log_error(title=_("PWA App"), message=_("Document is missing"))
        return {"data": None}

    doc = frappe.get_doc("Number Card", docname)

    currency = doc.currency if doc.currency else None
    if currency and frappe.db.exists("Currency", currency):
        currency_doc = frappe.get_doc("Currency", currency)
    
    if not doc:
        frappe.log_error(title=_("PWA App"), message=_(f"Number Card '{docname}' not found"))
        return {"data": None}

    if doc.type != "Custom":
        value = get_result(doc, doc.filters_json)
        formatted_value = format_number(value)
        if doc.function != "Count" and currency:
            formatted_value = f'{currency_doc.symbol} {formatted_value}'

        return {
            "data" : {
                "name": doc.label.upper(),
                "colorText": f'text-[{doc.color}]' if doc.color else 'text-gray-600',
                "value": formatted_value,
                "color": doc.color,
            }
        }

    else:
        custom_value = frappe.call(doc.method)
        value = custom_value.get("value")
        formatted_value = format_number(value)

        if custom_value.get("fieldtype") == "Currency" and currency:
            formatted_value = f'{currency_doc.symbol} {formatted_value}'

        return {
            "data" : {
                "name": doc.label.upper(),
                "colorText": f'text-[{doc.color}]' if doc.color else 'text-gray-600',
                "value": formatted_value,
                "colorText": doc.color
            }
        }
