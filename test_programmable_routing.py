"""
Test Script: Programmable Substitution Routing for Tool Owner / Distributor.
Verifies:
1. SAME_VARIANT_DIFF_BRAND (Cross-brand equivalent, e.g. Tiger 65g for Parle-G 65g)
2. SAME_BRAND_DIFF_VARIANT (Brand loyalty/upgrade, e.g. Parle-G 130g for Parle-G 65g)
3. Category-specific overrides
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.agents.graph_agent import GraphResolverAgent
from app.models.schemas import (
    ExtractedRawItem,
    SubstitutionPolicy,
    SubstitutionStrategy
)


def run_programmable_routing_test():
    print("=========================================================================")
    print("⚙️  Testing Programmable Substitution Routing for Distributor Owner")
    print("=========================================================================\n")

    agent = GraphResolverAgent()

    test_items = [
        ExtractedRawItem(raw_text="5 peti parle g chhota", normalized_name="Parle-G 65g", quantity=5.0),
        ExtractedRawItem(raw_text="3 carton dettol sabun", normalized_name="Dettol Soap 75g", quantity=3.0)
    ]

    # -------------------------------------------------------------------------
    # Scenario A: Owner configures "SAME_VARIANT_DIFF_BRAND"
    # Expected: Parle-G 65g -> Britannia Tiger 65g; Dettol 75g -> Lifebuoy 75g
    # -------------------------------------------------------------------------
    policy_cross_brand = SubstitutionPolicy(
        default_strategy=SubstitutionStrategy.SAME_VARIANT_DIFF_BRAND,
        max_substitutes_per_item=1
    )
    print("🔹 [Policy A]: Strategy = 'SAME_VARIANT_DIFF_BRAND' (Cross-brand identical variant)")
    cart_a = agent.run(test_items, policy=policy_cross_brand)

    parle_sub_a = cart_a.items[0].substitutes[0]
    dettol_sub_a = cart_a.items[1].substitutes[0]
    print(f"  • Parle-G 65g (OOS) -> Suggested: {parle_sub_a.name} ({parle_sub_a.brand}) | {parle_sub_a.reason}")
    print(f"  • Dettol 75g  (OOS) -> Suggested: {dettol_sub_a.name} ({dettol_sub_a.brand}) | {dettol_sub_a.reason}")

    assert "Tiger" in parle_sub_a.name
    assert "Lifebuoy" in dettol_sub_a.name
    print("  ✅ Scenario A passed: Cross-brand direct equivalents prioritized!\n")

    # -------------------------------------------------------------------------
    # Scenario B: Owner configures "SAME_BRAND_DIFF_VARIANT"
    # Expected: Parle-G 65g -> Parle-G 130g; Dettol 75g -> Dettol 125g
    # -------------------------------------------------------------------------
    policy_same_brand = SubstitutionPolicy(
        default_strategy=SubstitutionStrategy.SAME_BRAND_DIFF_VARIANT,
        max_substitutes_per_item=1
    )
    print("🔹 [Policy B]: Strategy = 'SAME_BRAND_DIFF_VARIANT' (Brand loyalty / pack upgrade)")
    cart_b = agent.run(test_items, policy=policy_same_brand)

    parle_sub_b = cart_b.items[0].substitutes[0]
    dettol_sub_b = cart_b.items[1].substitutes[0]
    print(f"  • Parle-G 65g (OOS) -> Suggested: {parle_sub_b.name} ({parle_sub_b.brand}) | {parle_sub_b.reason}")
    print(f"  • Dettol 75g  (OOS) -> Suggested: {dettol_sub_b.name} ({dettol_sub_b.brand}) | {dettol_sub_b.reason}")

    assert "Parle-G" in parle_sub_b.name
    assert "Dettol" in dettol_sub_b.name
    print("  ✅ Scenario B passed: Same-brand pack upgrades prioritized!\n")

    # -------------------------------------------------------------------------
    # Scenario C: Category-Specific Hybrid Override
    # Biscuits -> Cross-brand; Personal Care -> Same-brand
    # -------------------------------------------------------------------------
    policy_hybrid = SubstitutionPolicy(
        default_strategy=SubstitutionStrategy.SAME_VARIANT_DIFF_BRAND,
        category_overrides={
            "Personal Care": SubstitutionStrategy.SAME_BRAND_DIFF_VARIANT
        },
        max_substitutes_per_item=1
    )
    print("🔹 [Policy C]: Category Override: Biscuits=Cross-Brand, Personal Care=Same-Brand")
    cart_c = agent.run(test_items, policy=policy_hybrid)

    parle_sub_c = cart_c.items[0].substitutes[0]
    dettol_sub_c = cart_c.items[1].substitutes[0]
    print(f"  • Biscuits: Parle-G 65g -> {parle_sub_c.name} ({parle_sub_c.brand})")
    print(f"  • Personal Care: Dettol 75g -> {dettol_sub_c.name} ({dettol_sub_c.brand})")

    assert "Tiger" in parle_sub_c.name
    assert "Dettol" in dettol_sub_c.name
    print("  ✅ Scenario C passed: Category-level overrides functioning perfectly!\n")

    print("🎉 All programmable substitution routing policies verified successfully!")


if __name__ == "__main__":
    run_programmable_routing_test()

