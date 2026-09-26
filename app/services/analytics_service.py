"""
Analytics & Margin Intelligence Service for MandiMate.
Covers:
1. Margin Intelligence per Product & Family (Brand / Category)
2. Sales Velocity & FSN Classification (Fast, Slow, Non-moving)
3. Distributor Reorder Point (ROP) Auto-Trigger Alerts
4. Revenue Recovery Tracking (Sales saved by Knowledge Graph substitutes)
"""

from typing import List, Dict, Literal
from app.services.inventory_graph import FMCGInventoryGraph
from app.models.schemas import (
    ProductMarginData,
    FamilyMarginSummary,
    SKUPerformanceMetric,
    DistributorROPAlert,
    RevenueRecoveryReport,
    CartSummary
)


class AnalyticsService:
    """Core intelligence service for supply chain analytics and auto-triggers."""

    def __init__(self, inventory_graph: FMCGInventoryGraph):
        self.graph = inventory_graph
        # In-memory tracking for recovered revenue ledger
        self.total_orders = 0
        self.total_oos_items = 0
        self.substitutes_offered = 0
        self.substitutes_accepted = 0
        self.potential_revenue_lost = 0.0
        self.revenue_recovered = 0.0

    # -------------------------------------------------------------------------
    # 1. Margin Intelligence
    # -------------------------------------------------------------------------
    def get_all_product_margins(self) -> List[ProductMarginData]:
        """Calculates margin amount and gross margin percentage for every SKU."""
        margins: List[ProductMarginData] = []
        for sku_id, prod in self.graph.products.items():
            ws_price = prod.get("wholesale_price_per_carton", 0.0)
            cost = prod.get("purchase_cost_per_carton", 0.0)
            margin_amt = ws_price - cost
            margin_pct = (margin_amt / ws_price * 100) if ws_price > 0 else 0.0

            margins.append(
                ProductMarginData(
                    sku_id=sku_id,
                    name=prod["name"],
                    brand=prod["brand"],
                    category=prod["category"],
                    wholesale_price_per_carton=ws_price,
                    purchase_cost_per_carton=cost,
                    margin_per_carton=round(margin_amt, 2),
                    margin_pct=round(margin_pct, 2),
                    mrp_per_unit=prod.get("mrp_per_unit", 0.0),
                    units_per_carton=prod.get("units_per_carton", 1)
                )
            )
        # Sort by highest margin % first
        margins.sort(key=lambda x: x.margin_pct, reverse=True)
        return margins

    def get_family_margins(self, family_type: Literal["BRAND", "CATEGORY"] = "CATEGORY") -> List[FamilyMarginSummary]:
        """Aggregates margin and inventory performance across Brand or Category families."""
        families: Dict[str, List[ProductMarginData]] = {}
        for m in self.get_all_product_margins():
            key = m.brand if family_type == "BRAND" else m.category
            families.setdefault(key, []).append(m)

        summaries: List[FamilyMarginSummary] = []
        for family_name, items in families.items():
            avg_margin = sum(i.margin_pct for i in items) / len(items)
            highest_sku = max(items, key=lambda x: x.margin_pct)
            lowest_sku = min(items, key=lambda x: x.margin_pct)

            # Calculate total inventory value in warehouse for this family
            total_val = sum(
                self.graph.products[i.sku_id].get("stock_cartons", 0) * i.wholesale_price_per_carton
                for i in items
            )

            summaries.append(
                FamilyMarginSummary(
                    family_name=family_name,
                    family_type=family_type,
                    sku_count=len(items),
                    avg_margin_pct=round(avg_margin, 2),
                    highest_margin_sku=f"{highest_sku.name} ({highest_sku.margin_pct}%)",
                    lowest_margin_sku=f"{lowest_sku.name} ({lowest_sku.margin_pct}%)",
                    total_inventory_value=round(total_val, 2)
                )
            )

        summaries.sort(key=lambda x: x.avg_margin_pct, reverse=True)
        return summaries

    # -------------------------------------------------------------------------
    # 2. Sales Velocity & FSN Analytics (Fast, Slow, Non-Moving)
    # -------------------------------------------------------------------------
    def get_fsn_analytics(self) -> List[SKUPerformanceMetric]:
        """
        Classifies SKUs into Fast-Moving (F), Slow-Moving (S), or Non-Moving (N).
        Also calculates Days of Inventory Left (Stock / Daily Velocity).
        """
        metrics: List[SKUPerformanceMetric] = []
        for sku_id, prod in self.graph.products.items():
            stock = prod.get("stock_cartons", 0)
            velocity = prod.get("daily_sales_velocity", 1.0)
            days_left = round((stock / velocity), 1) if velocity > 0 else 999.0
            growth = prod.get("weekly_growth_pct", 0.0)

            # FMCG classification benchmark
            if velocity >= 12.0:
                classification = "FAST"
            elif velocity >= 4.0:
                classification = "SLOW"
            else:
                classification = "NON_MOVING"

            metrics.append(
                SKUPerformanceMetric(
                    sku_id=sku_id,
                    name=prod["name"],
                    brand=prod["brand"],
                    category=prod["category"],
                    current_stock_cartons=stock,
                    daily_sales_velocity=velocity,
                    days_of_inventory=days_left,
                    fsn_classification=classification,
                    weekly_growth_pct=growth
                )
            )

        # Sort: Fast movers first, then by lowest days of inventory (urgent attention)
        metrics.sort(key=lambda x: (x.fsn_classification != "FAST", x.days_of_inventory))
        return metrics

    # -------------------------------------------------------------------------
    # 3. Distributor Reorder Point (ROP) Auto-Trigger Alerts
    # -------------------------------------------------------------------------
    def get_distributor_rop_alerts(self) -> List[DistributorROPAlert]:
        """
        Evaluates current warehouse inventory against Reorder Point (ROP):
        ROP = (Daily Velocity * Supplier Lead Time) + Safety Stock
        Generates auto-trigger replenishment alerts when stock <= ROP.
        """
        alerts: List[DistributorROPAlert] = []
        for sku_id, prod in self.graph.products.items():
            current_stock = prod.get("stock_cartons", 0)
            velocity = prod.get("daily_sales_velocity", 5.0)
            lead_time = prod.get("supplier_lead_time_days", 3)
            safety_stock = prod.get("safety_stock_cartons", 20)

            rop = int((velocity * lead_time) + safety_stock)

            if current_stock <= rop:
                if current_stock == 0:
                    urgency = "CRITICAL"
                elif current_stock < safety_stock:
                    urgency = "HIGH"
                else:
                    urgency = "NORMAL"

                suggested_po = max((rop * 2) - current_stock, 50)

                alerts.append(
                    DistributorROPAlert(
                        sku_id=sku_id,
                        product_name=prod["name"],
                        brand=prod["brand"],
                        current_stock=current_stock,
                        reorder_point=rop,
                        safety_stock=safety_stock,
                        suggested_po_cartons=suggested_po,
                        urgency=urgency,
                        supplier_lead_time_days=lead_time
                    )
                )

        # Sort: CRITICAL first, then HIGH
        order = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2}
        alerts.sort(key=lambda x: order.get(x.urgency, 3))
        return alerts

    # -------------------------------------------------------------------------
    # 4. Revenue Recovery Tracker (Substitute ROI Moat)
    # -------------------------------------------------------------------------
    def record_cart_analytics(self, cart: CartSummary, accepted_substitutes_count: int = None):
        """Records an ordering event and measures revenue recovered via substitutes."""
        self.total_orders += 1
        for item in cart.items:
            if item.status in ("OUT_OF_STOCK", "PARTIAL_STOCK"):
                self.total_oos_items += 1
                lost_val = item.requested_cartons * item.wholesale_price_per_carton
                self.potential_revenue_lost += lost_val

                if item.substitutes:
                    self.substitutes_offered += 1
                    # By default assume the primary substitute was accepted
                    chosen_sub = item.substitutes[0]
                    recovered_val = item.requested_cartons * chosen_sub.wholesale_price_per_carton
                    self.revenue_recovered += recovered_val
                    self.substitutes_accepted += 1

    def get_revenue_recovery_report(self) -> RevenueRecoveryReport:
        """Returns the summary report showing how much GMV MandiMate saved."""
        rate = (self.revenue_recovered / self.potential_revenue_lost * 100) if self.potential_revenue_lost > 0 else 0.0
        return RevenueRecoveryReport(
            total_orders_analyzed=self.total_orders,
            total_oos_items_encountered=self.total_oos_items,
            substitutes_offered=self.substitutes_offered,
            substitutes_accepted=self.substitutes_accepted,
            potential_revenue_lost=round(self.potential_revenue_lost, 2),
            revenue_recovered=round(self.revenue_recovered, 2),
            recovery_rate_pct=round(rate, 2)
        )

