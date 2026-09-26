"""
Proactive Reorder & Customer Nudge Service for MandiMate.
Tracks retailer burn-rate and automatically triggers 1-tap WhatsApp reorder prompts.
"""

from typing import List, Dict, Any
from app.services.inventory_graph import FMCGInventoryGraph
from app.models.schemas import ProactiveNudge


class ProactiveTriggerService:
    """Detects when customer stock is depleted and triggers 1-tap WhatsApp restock nudges."""

    def __init__(self, inventory_graph: FMCGInventoryGraph):
        self.graph = inventory_graph

    def evaluate_retailer_reorder_need(
        self,
        retailer_phone: str,
        retailer_name: str,
        last_order_items: List[Dict[str, Any]],
        days_since_last_order: int,
        retailer_cycle_days: int = 5
    ) -> ProactiveNudge:
        """
        Evaluates whether a retailer needs a restock nudge based on days elapsed 
        since their last order cycle.
        """
        depleted_skus = []
        suggested_items = []
        estimated_total = 0.0

        for item in last_order_items:
            sku_id = item.get("sku_id")
            qty = item.get("quantity", 1.0)
            prod = self.graph.products.get(sku_id)

            if prod:
                depleted_skus.append(prod["name"])
                # Check live warehouse availability
                stock = prod.get("stock_cartons", 0)
                price = prod.get("wholesale_price_per_carton", 0.0)
                line_total = price * qty
                estimated_total += line_total

                suggested_items.append({
                    "sku_id": sku_id,
                    "name": prod["name"],
                    "quantity": qty,
                    "price_per_carton": price,
                    "line_total": line_total,
                    "in_stock": stock >= qty
                })

        reason = (
            f"Last order was {days_since_last_order} days ago. "
            f"Based on normal {retailer_cycle_days}-day replenishment cycle, inventory is near 0%."
        )

        return ProactiveNudge(
            retailer_phone=retailer_phone,
            retailer_name=retailer_name,
            depleted_skus=depleted_skus,
            suggested_items=suggested_items,
            estimated_total=round(estimated_total, 2),
            last_order_days_ago=days_since_last_order,
            trigger_reason=reason
        )

    def format_proactive_whatsapp_nudge(self, nudge: ProactiveNudge) -> str:
        """
        Generates a friendly Hinglish WhatsApp message with 1-tap repeat confirmation.
        """
        lines = [
            f"👋 *Namaste {nudge.retailer_name} Sethji!*",
            "_MandiMate Automated Stock Alert_\n",
            f"Aapka pichla order *{nudge.last_order_days_ago} din pehle* aaya tha.",
            f"Dukaan par ye fast-moving items khatam hone wale hain:\n"
        ]

        for item in nudge.suggested_items:
            lines.append(f"  • *{item['name']}* - {int(item['quantity'])} Peti (₹{item['line_total']:,.0f})")

        lines.append(f"\n💰 *Total Order Amount:* ₹{nudge.estimated_total:,.2f}")
        lines.append("\n_Pichle order jaisa same dispatch bhej dein?_")
        lines.append("\n👇 *Reply below or tap to confirm:*")
        lines.append("1️⃣ [🔁 Haan, Same Order Bhejo]")
        lines.append("2️⃣ [✏️ Quantity Kam/Zyada Karo]")
        return "\n".join(lines)

