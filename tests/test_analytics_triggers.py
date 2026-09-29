"""
Comprehensive Test Script for MandiMitra Intelligence Layers (Ideas 1 - 4):
1. Margin Intelligence per Product & Family
2. Sales Velocity & FSN Analytics
3. Distributor Reorder Point (ROP) Auto-Trigger Alerts
4. Customer Proactive Restock Nudges (WhatsApp 1-Tap Repeat)
5. Revenue Recovery Tracking (Substitute ROI)
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mandimitra.services.inventory_graph import FMCGInventoryGraph
from mandimitra.services.analytics_service import AnalyticsService
from mandimitra.services.trigger_service import ProactiveTriggerService
from mandimitra.services.whatsapp_composer import WhatsAppPayloadComposer
from mandimitra.models.schemas import ExtractedRawItem


def test_analytics_and_triggers():
    print("=========================================================================")
    print("📊 MandiMitra Autonomous Supply Chain & Margin Intelligence Engine")
    print("=========================================================================\n")

    # Initialize Graph & Services
    graph = FMCGInventoryGraph()
    analytics = AnalyticsService(graph)
    triggers = ProactiveTriggerService(graph)

    # -------------------------------------------------------------------------
    # 1. Test Margin Intelligence
    # -------------------------------------------------------------------------
    print("💰 [1. Margin Intelligence per Product & Family]:")
    product_margins = analytics.get_all_product_margins()
    print("  Top 3 Highest Margin Products:")
    for pm in product_margins[:3]:
        print(f"   • {pm.name} ({pm.brand}): Wholesale ₹{pm.wholesale_price_per_carton} | Cost ₹{pm.purchase_cost_per_carton} | Margin: {pm.margin_pct}% (₹{pm.margin_per_carton}/peti)")

    print("\n  Category Family Margins:")
    category_margins = analytics.get_family_margins(family_type="CATEGORY")
    for cm in category_margins:
        print(f"   • [{cm.family_name}]: Avg Margin: {cm.avg_margin_pct}% | SKUs: {cm.sku_count} | Total Stock Value: ₹{cm.total_inventory_value:,.2f}")

    assert len(product_margins) > 0
    assert any(cm.family_name == "Personal Care" for cm in category_margins)

    # -------------------------------------------------------------------------
    # 2. Test Sales Velocity & FSN Analytics
    # -------------------------------------------------------------------------
    print("\n📈 [2. Sales Velocity & FSN Classification]:")
    fsn_metrics = analytics.get_fsn_analytics()
    fast_movers = [m for m in fsn_metrics if m.fsn_classification == "FAST"]
    slow_movers = [m for m in fsn_metrics if m.fsn_classification == "SLOW"]

    print(f"  • Fast-Moving SKUs (F): {len(fast_movers)} items")
    for fm in fast_movers[:3]:
        print(f"     - {fm.name}: Velocity {fm.daily_sales_velocity} cartons/day | {fm.days_of_inventory} days inventory left")

    print(f"  • Slow-Moving SKUs (S): {len(slow_movers)} items")
    for sm in slow_movers[:2]:
        print(f"     - {sm.name}: Velocity {sm.daily_sales_velocity} cartons/day | {sm.days_of_inventory} days inventory left")

    assert len(fast_movers) > 0

    # -------------------------------------------------------------------------
    # 3. Test Distributor Reorder Point (ROP) Alerts
    # -------------------------------------------------------------------------
    print("\n🚨 [3. Distributor Reorder Point (ROP) Auto-Trigger Alerts]:")
    rop_alerts = analytics.get_distributor_rop_alerts()
    for alert in rop_alerts:
        print(f"   • [{alert.urgency}] {alert.product_name} ({alert.brand}): Current Stock: {alert.current_stock} Peti | ROP: {alert.reorder_point} | Suggested PO: {alert.suggested_po_cartons} Peti")

    assert any(a.urgency == "CRITICAL" for a in rop_alerts)  # Parle-G 65g or Dettol 75g (stock=0)

    # -------------------------------------------------------------------------
    # 4. Test Customer Proactive Restock Nudge (Burn Rate Tracker)
    # -------------------------------------------------------------------------
    print("\n📱 [4. Customer Proactive Restock Nudge]:")
    last_order = [
        {"sku_id": "SKU_MAGGI_MASALA_70G", "quantity": 10.0},
        {"sku_id": "SKU_BRITANNIA_TIGER_65G", "quantity": 5.0}
    ]
    # Retailer ordered 6 days ago (cycle is 5 days)
    nudge = triggers.evaluate_retailer_reorder_need(
        retailer_phone="+919876543210",
        retailer_name="Ramesh",
        last_order_items=last_order,
        days_since_last_order=6,
        retailer_cycle_days=5
    )

    print(f"  • Nudge Triggered: {nudge.trigger_reason}")
    print(f"  • Suggested Repeat Value: ₹{nudge.estimated_total:,.2f}")
    whatsapp_nudge_text = triggers.format_proactive_whatsapp_nudge(nudge)
    print("\n  --- WhatsApp Nudge Preview ---")
    print(whatsapp_nudge_text)
    print("  ------------------------------")

    # Generate Meta button payload for the nudge
    nudge_payload = WhatsAppPayloadComposer.create_proactive_nudge_buttons("+919876543210", nudge)
    assert nudge_payload["type"] == "interactive"
    assert nudge_payload["interactive"]["type"] == "button"

    # -------------------------------------------------------------------------
    # 5. Test Revenue Recovery Tracking (Substitute Moat)
    # -------------------------------------------------------------------------
    print("\n🛡️ [5. Revenue Recovery Tracking]:")
    # Simulate an order with OOS items to test revenue recovery
    simulated_order = [
        ExtractedRawItem(raw_text="10 peti parle g chhota", normalized_name="Parle-G 65g", quantity=10.0),
        ExtractedRawItem(raw_text="5 carton dettol sabun", normalized_name="Dettol Soap 75g", quantity=5.0)
    ]
    cart = graph.resolve_raw_order(simulated_order)
    analytics.record_cart_analytics(cart)

    recovery_report = analytics.get_revenue_recovery_report()
    print(f"  • Total Orders Analyzed: {recovery_report.total_orders_analyzed}")
    print(f"  • Total OOS Items Encountered: {recovery_report.total_oos_items_encountered}")
    print(f"  • Potential Revenue Lost to Stockouts: ₹{recovery_report.potential_revenue_lost:,.2f}")
    print(f"  • Revenue Recovered via Substitutes: ₹{recovery_report.revenue_recovered:,.2f}")
    print(f"  • Recovery Rate: {recovery_report.recovery_rate_pct:.1f}%")

    assert recovery_report.revenue_recovered > 0
    assert recovery_report.recovery_rate_pct > 80.0

    # -------------------------------------------------------------------------
    # 6. Executive Morning Briefing to Distributor Owner
    # -------------------------------------------------------------------------
    print("\n🌅 [6. WhatsApp Executive Morning Briefing to Distributor]:")
    briefing = WhatsAppPayloadComposer.create_distributor_morning_briefing(
        owner_phone="+919999988888",
        rop_alerts=rop_alerts,
        top_family_margins=category_margins,
        recovery_report=recovery_report
    )
    print(briefing)

    print("\n🎉 All 4 Intelligence Layers (Margins, Velocity/FSN, Auto-Triggers, Revenue Recovery) verified successfully!")


if __name__ == "__main__":
    test_analytics_and_triggers()

