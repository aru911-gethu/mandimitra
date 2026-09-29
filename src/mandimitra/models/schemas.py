from enum import Enum
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class SubstitutionStrategy(str, Enum):
    """Programmable routing strategy for out-of-stock product substitutions."""
    SAME_VARIANT_DIFF_BRAND = "SAME_VARIANT_DIFF_BRAND"  # e.g., Tiger 65g for Parle-G 65g (cross-brand equivalent)
    SAME_BRAND_DIFF_VARIANT = "SAME_BRAND_DIFF_VARIANT"  # e.g., Parle-G 130g for Parle-G 65g (brand loyalty / pack size upgrade)
    HIGHEST_MARGIN = "HIGHEST_MARGIN"                    # Sort by highest distributor profit margin
    HIGHEST_STOCK = "HIGHEST_STOCK"                      # Sort by warehouse inventory clearance
    BALANCED = "BALANCED"                                # Smart mix: 1 cross-brand + 1 brand variant


class SubstitutionPolicy(BaseModel):
    """Configurable distributor substitution policy."""
    default_strategy: SubstitutionStrategy = SubstitutionStrategy.BALANCED
    category_overrides: Dict[str, SubstitutionStrategy] = Field(
        default_factory=dict,
        description="Optional category-specific overrides, e.g. {'Personal Care': 'SAME_BRAND_DIFF_VARIANT'}"
    )
    max_substitutes_per_item: int = 2
    min_similarity_threshold: float = 0.6


class ExtractedRawItem(BaseModel):
    """Raw item parsed by Agent 1 from voice note audio or handwritten image."""
    raw_text: str = Field(description="Raw string extracted from voice or image, e.g. '5 peti parle g chhota'")
    normalized_name: str = Field(description="Identified product name, e.g. 'Parle-G 65g'")
    quantity: float = Field(default=1.0, description="Quantity requested")
    unit: str = Field(default="carton", description="Unit such as peti, carton, dabba, dozen, piece")
    confidence: float = Field(default=0.9, description="Confidence score between 0 and 1")


class SubstituteItem(BaseModel):
    """An alternative in-stock product discovered via the Knowledge Graph."""
    sku_id: str
    name: str
    brand: str
    pack_size: str
    units_per_carton: int
    wholesale_price_per_carton: float
    mrp_per_unit: float
    stock_cartons: int
    similarity_score: float
    reason: str = Field(description="Explanation e.g. 'Identical Glucose biscuit category with 120 cartons in stock'")


class ResolvedItem(BaseModel):
    """Status of a parsed item after Agent 2 resolves it against the Knowledge Graph."""
    raw_query: str
    matched_sku_id: Optional[str] = None
    matched_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    status: Literal["IN_STOCK", "OUT_OF_STOCK", "PARTIAL_STOCK", "NOT_FOUND"]
    requested_cartons: float
    available_cartons: int = 0
    wholesale_price_per_carton: float = 0.0
    line_total: float = 0.0
    substitutes: List[SubstituteItem] = Field(default_factory=list)


class CartSummary(BaseModel):
    """Wholesale cart ready for WhatsApp Flow confirmation."""
    distributor_id: str = "DIST_MANDI_01"
    retailer_phone: str = ""
    total_requested_items: int = 0
    in_stock_items_count: int = 0
    oos_items_count: int = 0
    estimated_total_amount: float = 0.0
    items: List[ResolvedItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Analytics, Margins, Velocity & Auto-Trigger Schemas (Ideas 1 - 4)
# ---------------------------------------------------------------------------

class ProductMarginData(BaseModel):
    """Profit margin intelligence per product."""
    sku_id: str
    name: str
    brand: str
    category: str
    wholesale_price_per_carton: float
    purchase_cost_per_carton: float
    margin_per_carton: float
    margin_pct: float
    mrp_per_unit: float
    units_per_carton: int


class FamilyMarginSummary(BaseModel):
    """Aggregated profit margin per Brand or Category family."""
    family_name: str
    family_type: Literal["BRAND", "CATEGORY"]
    sku_count: int
    avg_margin_pct: float
    highest_margin_sku: str
    lowest_margin_sku: str
    total_inventory_value: float


class SKUPerformanceMetric(BaseModel):
    """Sales velocity and FSN (Fast, Slow, Non-moving) classification."""
    sku_id: str
    name: str
    brand: str
    category: str
    current_stock_cartons: int
    daily_sales_velocity: float  # cartons sold per day
    days_of_inventory: float     # current_stock / velocity
    fsn_classification: Literal["FAST", "SLOW", "NON_MOVING"]
    weekly_growth_pct: float = 0.0


class DistributorROPAlert(BaseModel):
    """Auto-trigger alert when warehouse stock hits Reorder Point (ROP)."""
    sku_id: str
    product_name: str
    brand: str
    current_stock: int
    reorder_point: int
    safety_stock: int
    suggested_po_cartons: int
    urgency: Literal["CRITICAL", "HIGH", "NORMAL"]
    supplier_lead_time_days: int


class ProactiveNudge(BaseModel):
    """Predictive restock notification for a retail customer."""
    retailer_phone: str
    retailer_name: str
    depleted_skus: List[str]
    suggested_items: List[Dict[str, Any]]
    estimated_total: float
    last_order_days_ago: int
    trigger_reason: str


class RevenueRecoveryReport(BaseModel):
    """Tracks revenue saved by MandiMitra substitute engine on out-of-stock items."""
    total_orders_analyzed: int
    total_oos_items_encountered: int
    substitutes_offered: int
    substitutes_accepted: int
    potential_revenue_lost: float
    revenue_recovered: float
    recovery_rate_pct: float

