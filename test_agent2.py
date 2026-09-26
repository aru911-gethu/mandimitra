"""
Test Script for MandiMate Sub-Agent 2 (Knowledge Graph & Substitute Resolver)
Simulates realistic raw input coming from Agent 1 (Handwriting/Voice Parser).
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.agents.graph_agent import GraphResolverAgent
from app.models.schemas import ExtractedRawItem
from app.services.whatsapp_composer import WhatsAppPayloadComposer


def test_agent_2_pipeline():
    print("=================================================================")
    print("🚀 Initializing MandiMate Sub-Agent 2 (Knowledge Graph Resolver)")
    print("=================================================================\n")

    agent = GraphResolverAgent()

    # Simulated output from Agent 1 (Voice / Handwritten note parser)
    mock_agent_1_extracted_items = [
        ExtractedRawItem(
            raw_text="10 peti parle g chhota",
            normalized_name="Parle-G 65g",
            quantity=10.0,
            unit="peti",
            confidence=0.95
        ),
        ExtractedRawItem(
            raw_text="5 peti maggi noodles",
            normalized_name="Maggi Masala Noodles",
            quantity=5.0,
            unit="peti",
            confidence=0.98
        ),
        ExtractedRawItem(
            raw_text="3 carton dettol sabun",
            normalized_name="Dettol Soap 75g",
            quantity=3.0,
            unit="carton",
            confidence=0.92
        ),
        ExtractedRawItem(
            raw_text="2 peti fortune sarson tel",
            normalized_name="Fortune Mustard Oil 1L",
            quantity=2.0,
            unit="peti",
            confidence=0.96
        )
    ]

    print("📥 [Input from Agent 1]:")
    for item in mock_agent_1_extracted_items:
        print(f"  - '{item.raw_text}' -> Normalized: '{item.normalized_name}', Qty: {item.quantity} {item.unit}")

    print("\n🔍 Traversing Knowledge Graph to match SKUs, check stock, and discover substitutes...")
    cart_summary = agent.run(mock_agent_1_extracted_items)

    print("\n📊 [Agent 2 Graph Resolution Results]:")
    print(f"  • Total Items Processed: {cart_summary.total_requested_items}")
    print(f"  • In Stock Items: {cart_summary.in_stock_items_count}")
    print(f"  • Out of Stock Items: {cart_summary.oos_items_count}")
    print(f"  • Estimated Order Total: ₹{cart_summary.estimated_total_amount:,.2f}")

    print("\n📱 [Generated WhatsApp Message for Retailer]:")
    whatsapp_text = agent.format_whatsapp_summary(cart_summary)
    print(whatsapp_text)

    # Assertions
    assert cart_summary.total_requested_items == 4
    assert cart_summary.in_stock_items_count == 2  # Maggi & Fortune
    assert cart_summary.oos_items_count == 2       # Parle-G & Dettol

    # Check that Parle-G substitutes were discovered via Graph
    parle_g_res = next(i for i in cart_summary.items if "parle g" in i.raw_query.lower())
    assert parle_g_res.status == "OUT_OF_STOCK"
    assert len(parle_g_res.substitutes) >= 1
    assert any("Tiger" in s.name for s in parle_g_res.substitutes)

    # Check that Dettol soap substitute was discovered via Graph
    dettol_res = next(i for i in cart_summary.items if "dettol" in i.raw_query.lower())
    assert dettol_res.status == "OUT_OF_STOCK"
    assert len(dettol_res.substitutes) >= 1
    assert any("Lifebuoy" in s.name for s in dettol_res.substitutes)

    # Verify Meta WhatsApp Interactive List payload generation
    payload = WhatsAppPayloadComposer.create_interactive_list_message("+919876543210", cart_summary)
    assert payload["type"] == "interactive"
    assert payload["interactive"]["type"] == "list"
    assert len(payload["interactive"]["action"]["sections"]) == 2  # In-Stock & Substitutes

    print(f"\n📦 Generated Meta WhatsApp Interactive Payload successfully:")
    print(f"  • Recipient: {payload['to']}")
    print(f"  • Button: {payload['interactive']['action']['button']}")
    print(f"  • Sections: {[s['title'] for s in payload['interactive']['action']['sections']]}")

    print("\n✅ All assertions passed successfully! Agent 2 & WhatsApp Composer are functioning perfectly.")


if __name__ == "__main__":
    test_agent_2_pipeline()
