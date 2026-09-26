"""
WhatsApp Message Composer for MandiMate.
Generates compliant Meta WhatsApp Business Cloud API JSON payloads:
1. Interactive List Messages (with In-Stock & Substitute rows)
2. Interactive Reply Buttons
3. WhatsApp Flow trigger payload
"""

from typing import Dict, Any
from app.models.schemas import CartSummary


class WhatsAppPayloadComposer:
    """Composes native Meta WhatsApp Cloud API interactive payloads."""

    @staticmethod
    def create_interactive_list_message(to_phone: str, cart: CartSummary) -> Dict[str, Any]:
        """
        Builds a Meta-compliant 'interactive list' message.
        Allows the retailer to click 'Review & Confirm' to see all items and choose substitutes.
        """
        sections = []

        # Section 1: In-Stock items
        in_stock_rows = []
        for item in cart.items:
            if item.status == "IN_STOCK" and item.matched_sku_id:
                in_stock_rows.append({
                    "id": f"ACCEPT_{item.matched_sku_id}_{int(item.requested_cartons)}",
                    "title": f"✅ {item.matched_name[:24]}",
                    "description": f"{int(item.requested_cartons)} Peti @ ₹{item.wholesale_price_per_carton}/peti (₹{item.line_total:,.0f})"
                })

        if in_stock_rows:
            sections.append({
                "title": "In-Stock Items (Ready)",
                "rows": in_stock_rows[:10]  # Meta limit per section is 10
            })

        # Section 2: Recommended Substitutes for OOS items
        substitute_rows = []
        for item in cart.items:
            if item.status in ("OUT_OF_STOCK", "PARTIAL_STOCK") and item.substitutes:
                for sub in item.substitutes:
                    substitute_rows.append({
                        "id": f"SUB_{sub.sku_id}_{int(item.requested_cartons)}",
                        "title": f"🔄 {sub.name[:24]}",
                        "description": f"Sub for {item.matched_name or item.raw_query[:15]}: ₹{sub.wholesale_price_per_carton}/peti"
                    })

        if substitute_rows:
            sections.append({
                "title": "Smart Substitutes (In Stock)",
                "rows": substitute_rows[:10]
            })

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {
                    "type": "text",
                    "text": "🛒 MandiMate Wholesale Order"
                },
                "body": {
                    "text": (
                        f"Namaste Sethji! We processed your shortage note.\n"
                        f"• {cart.in_stock_items_count} items in stock\n"
                        f"• {cart.oos_items_count} items substituted with warehouse inventory\n"
                        f"• Estimated Total: *₹{cart.estimated_total_amount:,.2f}*\n\n"
                        f"Tap below to review your cart & dispatch."
                    )
                },
                "footer": {
                    "text": "Har Jagah, Har Waqt, Mandi in Pocket!"
                },
                "action": {
                    "button": "View Cart & Dispatch",
                    "sections": sections
                }
            }
        }
        return payload

    @staticmethod
    def create_quick_confirm_buttons(to_phone: str, cart: CartSummary) -> Dict[str, Any]:
        """
        Creates an interactive button message to confirm or edit the order with 1 tap.
        """
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": (
                        f"📦 *Confirm Wholesale Dispatch?*\n\n"
                        f"Total Items: {cart.total_requested_items}\n"
                        f"Total Amount: *₹{cart.estimated_total_amount:,.2f}*\n\n"
                        f"Ready to push to warehouse dispatch?"
                    )
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "CONFIRM_DISPATCH",
                                "title": "✅ Confirm Order"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "EDIT_CART",
                                "title": "✏️ Edit Quantities"
                            }
                        }
                    ]
                }
            }
        }

    @staticmethod
    def create_proactive_nudge_buttons(to_phone: str, nudge: Any) -> Dict[str, Any]:
        """
        Builds a 1-tap repeat order message for a customer whose stock is depleted.
        """
        sku_summary = ", ".join([f"{int(i['quantity'])} Peti {i['name'][:18]}" for i in nudge.suggested_items[:3]])
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {
                    "type": "text",
                    "text": "⚡ MandiMate Restock Nudge"
                },
                "body": {
                    "text": (
                        f"Namaste {nudge.retailer_name} Sethji!\n\n"
                        f"Aapka pichla order {nudge.last_order_days_ago} din pehle aaya tha.\n"
                        f"Running low on: *{sku_summary}*.\n\n"
                        f"Repeat dispatch for *₹{nudge.estimated_total:,.2f}*?"
                    )
                },
                "footer": {
                    "text": "Har Jagah, Har Waqt, Mandi in Pocket!"
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "REPEAT_LAST_ORDER",
                                "title": "🔁 Haan, Repeat Karo"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "MODIFY_ITEMS",
                                "title": "✏️ Modify Cart"
                            }
                        }
                    ]
                }
            }
        }

    @staticmethod
    def create_distributor_morning_briefing(
        owner_phone: str,
        rop_alerts: list,
        top_family_margins: list,
        recovery_report: Any
    ) -> str:
        """
        Formats a daily WhatsApp executive briefing for the warehouse owner / distributor.
        """
        lines = [
            "🌅 *MandiMate Morning Executive Briefing*",
            "_Har Jagah, Har Waqt, Mandi in Pocket!_\n",
            "💰 *1. Profit Margins by Family:*",
        ]
        for f in top_family_margins[:3]:
            lines.append(f"  • *{f.family_name}*: {f.avg_margin_pct}% avg margin (Inventory: ₹{f.total_inventory_value:,.0f})")

        lines.append("\n⚠️ *2. Factory Reorder Alerts (ROP Trigger):*")
        critical_alerts = [a for a in rop_alerts if a.urgency in ("CRITICAL", "HIGH")]
        if critical_alerts:
            for a in critical_alerts[:3]:
                lines.append(
                    f"  • 🚨 *{a.product_name}* ({a.brand})\n"
                    f"    Stock: {a.current_stock} | ROP: {a.reorder_point} | Suggested PO: {a.suggested_po_cartons} Peti"
                )
        else:
            lines.append("  • ✅ All warehouse SKUs above safety stock.")

        lines.append("\n🛡️ *3. Revenue Recovered via Substitutes:*")
        lines.append(
            f"  • Total Saved: *₹{recovery_report.revenue_recovered:,.2f}* "
            f"({recovery_report.recovery_rate_pct:.1f}% recovery rate on OOS)"
        )
        lines.append("\n_Have a high-velocity trading day, Sethji! 🚀_")
        return "\n".join(lines)

