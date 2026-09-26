import json
from typing import List, Dict, Any, Optional
from app.services.inventory_graph import FMCGInventoryGraph
from app.models.schemas import ExtractedRawItem, CartSummary, SubstitutionPolicy, SubstitutionStrategy


class GraphResolverAgent:
    """
    Sub-Agent 2: Entity Resolution & Knowledge Graph Resolver.
    Supports programmable substitution routing policies selectable by the tool owner.
    """

    def __init__(self, seed_file: Optional[str] = None, policy: Optional[SubstitutionPolicy] = None):
        self.graph = FMCGInventoryGraph(seed_file, policy=policy)

    def run(self, raw_items: List[Dict[str, Any]], policy: Optional[SubstitutionPolicy] = None) -> CartSummary:
        """
        Processes a list of raw item dictionaries (or ExtractedRawItem instances)
        and returns a fully resolved CartSummary using the specified routing policy.
        """
        parsed_items: List[ExtractedRawItem] = []
        for item in raw_items:
            if isinstance(item, ExtractedRawItem):
                parsed_items.append(item)
            elif isinstance(item, dict):
                parsed_items.append(ExtractedRawItem(**item))

        return self.graph.resolve_raw_order(parsed_items, policy=policy)

    def format_whatsapp_summary(self, cart: CartSummary) -> str:
        """
        Formats the resolved cart into a friendly Hinglish summary suitable for 
        WhatsApp chat preview before the interactive bottom-sheet / clicker.
        """
        lines = [
            "🛒 *MandiMate Order Summary*",
            "_Har Jagah, Har Waqt, Mandi in Pocket!_\n",
            f"📦 *Total Items Requested:* {cart.total_requested_items}",
            f"✅ *In Stock:* {cart.in_stock_items_count}",
            f"⚠️ *Out of Stock / Alternatives:* {cart.oos_items_count}",
            "────────────────────────"
        ]

        for idx, item in enumerate(cart.items, 1):
            if item.status == "IN_STOCK":
                lines.append(
                    f"{idx}. ✅ *{item.matched_name}*\n"
                    f"   • Qty: {item.requested_cartons:.0f} Peti @ ₹{item.wholesale_price_per_carton}/peti\n"
                    f"   • Subtotal: ₹{item.line_total:,.2f}"
                )
            elif item.status == "OUT_OF_STOCK":
                lines.append(
                    f"{idx}. ❌ *{item.matched_name or item.raw_query}* (Out of Stock)\n"
                    f"   • Requested: {item.requested_cartons:.0f} Peti"
                )
                if item.substitutes:
                    lines.append("   👉 *Available Alternatives in Warehouse:*")
                    for sub in item.substitutes:
                        lines.append(
                            f"      🔹 *{sub.name}* (Stock: {sub.stock_cartons} Peti)\n"
                            f"         Rate: ₹{sub.wholesale_price_per_carton}/peti | {sub.reason}"
                        )
                else:
                    lines.append("   👉 _No direct substitute available today._")
            elif item.status == "PARTIAL_STOCK":
                lines.append(
                    f"{idx}. ⚠️ *{item.matched_name}* (Partial Stock)\n"
                    f"   • Requested: {item.requested_cartons:.0f} | Available: {item.available_cartons} Peti\n"
                    f"   • Subtotal: ₹{item.line_total:,.2f}"
                )
                if item.substitutes:
                    lines.append("   👉 *Need more? Available Alternatives:*")
                    for sub in item.substitutes:
                        lines.append(
                            f"      🔹 *{sub.name}* (Stock: {sub.stock_cartons} Peti)"
                        )

        lines.append("────────────────────────")
        lines.append(f"💰 *Estimated Cart Total:* ₹{cart.estimated_total_amount:,.2f}")
        lines.append("\n👇 _Tap below to review quantities or accept substitutes:_")
        return "\n".join(lines)

