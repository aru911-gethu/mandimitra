import json
import difflib
from pathlib import Path
from typing import List, Optional, Tuple
import networkx as nx

from app.models.schemas import (
    ExtractedRawItem,
    SubstituteItem,
    ResolvedItem,
    CartSummary,
    SubstitutionStrategy,
    SubstitutionPolicy
)


class FMCGInventoryGraph:
    """
    Knowledge Graph for FMCG Catalog & Substitute Resolution.
    Backed by NetworkX for sub-millisecond in-memory graph traversals.
    """

    def __init__(self, seed_file_path: Optional[str] = None, policy: Optional[SubstitutionPolicy] = None):
        self.graph = nx.DiGraph()
        self.alias_map: dict[str, str] = {}  # alias_lower -> sku_id
        self.products: dict[str, dict] = {}
        self.policy: SubstitutionPolicy = policy or SubstitutionPolicy()

        if seed_file_path:
            self.load_from_json(seed_file_path)
        else:
            default_path = Path(__file__).parent.parent / "mock_data" / "seed_fmcg.json"
            if default_path.exists():
                self.load_from_json(str(default_path))

    def get_effective_strategy(self, category: str, custom_policy: Optional[SubstitutionPolicy] = None) -> SubstitutionStrategy:
        """Determines the active substitution strategy taking category-level overrides into account."""
        active_policy = custom_policy or self.policy
        if category in active_policy.category_overrides:
            return active_policy.category_overrides[category]
        return active_policy.default_strategy

    def find_substitutes(
        self,
        sku_id: str,
        limit: Optional[int] = None,
        policy: Optional[SubstitutionPolicy] = None
    ) -> List[SubstituteItem]:
        """
        Programmable Knowledge Graph Traversal.
        Ranks in-stock alternatives according to the distributor owner's chosen strategy:
        - SAME_VARIANT_DIFF_BRAND: Identical pack/size from competing brand (e.g. Tiger 65g for Parle-G 65g)
        - SAME_BRAND_DIFF_VARIANT: Same brand, alternative pack/size (e.g. Parle-G 130g for Parle-G 65g)
        - HIGHEST_MARGIN: Sorted by distributor gross margin %
        - HIGHEST_STOCK: Sorted by warehouse inventory velocity / clearance
        - BALANCED: Smart blend (1 cross-brand equivalent + 1 same-brand variant)
        """
        source_prod = self.products.get(sku_id)
        if not source_prod:
            return []

        active_policy = policy or self.policy
        max_limit = limit or active_policy.max_substitutes_per_item
        strategy = self.get_effective_strategy(source_prod.get("category", ""), active_policy)

        source_brand = source_prod.get("brand", "").lower()
        source_subcat = source_prod.get("subcategory", "").lower()
        source_pack = source_prod.get("pack_size", "").lower().replace(" ", "")

        candidates: List[dict] = []
        visited = {sku_id}

        # Step 1: Collect direct explicit substitutes from graph edges
        for _, neighbor, edge_data in self.graph.out_edges(sku_id, data=True):
            if edge_data.get("rel") == "HAS_SUBSTITUTE" and neighbor not in visited:
                target_prod = self.products.get(neighbor)
                if target_prod and target_prod.get("stock_cartons", 0) > 0:
                    candidates.append({
                        "sku_id": neighbor,
                        "product": target_prod,
                        "edge_type": edge_data.get("sub_type", "GENERAL"),
                        "similarity_score": edge_data.get("similarity_score", 0.85),
                        "reason": edge_data.get("reason", "Direct substitute match"),
                        "is_explicit_edge": True
                    })
                    visited.add(neighbor)

        # Step 2: Sibling traversal via SUBCATEGORY or BRAND node
        subcat_node = f"SUBCAT_{source_prod.get('subcategory', '').upper().replace(' ', '_')}"
        brand_node = f"BRAND_{source_prod.get('brand', '').upper().replace(' ', '_')}"

        # Collect category siblings
        if self.graph.has_node(subcat_node):
            for node in self.graph.predecessors(subcat_node):
                if node not in visited and self.graph.nodes[node].get("node_type") == "PRODUCT":
                    prod = self.products.get(node)
                    if prod and prod.get("stock_cartons", 0) > 0:
                        candidates.append({
                            "sku_id": node,
                            "product": prod,
                            "edge_type": "CATEGORY_SIBLING",
                            "similarity_score": 0.75,
                            "reason": f"Same category ({prod['subcategory']}) with {prod['stock_cartons']} cartons available",
                            "is_explicit_edge": False
                        })
                        visited.add(node)

        # Collect brand siblings (for same-brand different variant search)
        if self.graph.has_node(brand_node):
            for node in self.graph.predecessors(brand_node):
                if node not in visited and self.graph.nodes[node].get("node_type") == "PRODUCT":
                    prod = self.products.get(node)
                    if prod and prod.get("stock_cartons", 0) > 0:
                        candidates.append({
                            "sku_id": node,
                            "product": prod,
                            "edge_type": "BRAND_SIBLING",
                            "similarity_score": 0.70,
                            "reason": f"Same brand ({prod['brand']}) with {prod['stock_cartons']} cartons available",
                            "is_explicit_edge": False
                        })
                        visited.add(node)

        # Step 3: Classify each candidate for routing
        for c in candidates:
            p = c["product"]
            c_brand = p.get("brand", "").lower()
            c_subcat = p.get("subcategory", "").lower()
            c_pack = p.get("pack_size", "").lower().replace(" ", "")

            is_same_brand = (c_brand == source_brand)
            is_cross_brand_same_variant = (not is_same_brand) and (c_subcat == source_subcat)
            is_exact_pack_match = (c_pack == source_pack)

            # Gross margin %: (Retail value - wholesale cost) / wholesale cost
            retail_carton_value = p.get("mrp_per_unit", 0.0) * p.get("units_per_carton", 1)
            wholesale_cost = p.get("wholesale_price_per_carton", 1.0)
            margin_pct = ((retail_carton_value - wholesale_cost) / wholesale_cost) if wholesale_cost > 0 else 0.0

            c["is_same_brand"] = is_same_brand
            c["is_cross_brand_same_variant"] = is_cross_brand_same_variant
            c["is_exact_pack_match"] = is_exact_pack_match
            c["margin_pct"] = margin_pct
            c["stock_cartons"] = p.get("stock_cartons", 0)

        # Step 4: Sort candidates according to the programmable strategy
        if strategy == SubstitutionStrategy.SAME_VARIANT_DIFF_BRAND:
            # Prioritize: 1) Cross-brand same subcategory, 2) Exact pack size, 3) Similarity score, 4) Stock
            candidates.sort(
                key=lambda x: (
                    x["is_cross_brand_same_variant"],
                    x["is_exact_pack_match"],
                    x["similarity_score"],
                    x["stock_cartons"]
                ),
                reverse=True
            )
        elif strategy == SubstitutionStrategy.SAME_BRAND_DIFF_VARIANT:
            # Prioritize: 1) Same brand, 2) Similarity score, 3) Stock
            candidates.sort(
                key=lambda x: (
                    x["is_same_brand"],
                    x["similarity_score"],
                    x["stock_cartons"]
                ),
                reverse=True
            )
        elif strategy == SubstitutionStrategy.HIGHEST_MARGIN:
            candidates.sort(
                key=lambda x: (x["margin_pct"], x["similarity_score"]),
                reverse=True
            )
        elif strategy == SubstitutionStrategy.HIGHEST_STOCK:
            candidates.sort(
                key=lambda x: (x["stock_cartons"], x["similarity_score"]),
                reverse=True
            )
        else:  # BALANCED
            # Provide 1 cross-brand equivalent + 1 same-brand upgrade if possible
            cross_brand = [c for c in candidates if c["is_cross_brand_same_variant"]]
            same_brand = [c for c in candidates if c["is_same_brand"]]

            balanced_list = []
            if cross_brand:
                cross_brand.sort(key=lambda x: (x["similarity_score"], x["stock_cartons"]), reverse=True)
                balanced_list.append(cross_brand[0])
            if same_brand:
                same_brand.sort(key=lambda x: (x["similarity_score"], x["stock_cartons"]), reverse=True)
                # Avoid duplicate
                if not balanced_list or same_brand[0]["sku_id"] != balanced_list[0]["sku_id"]:
                    balanced_list.append(same_brand[0])

            # Fill remaining slots
            for c in sorted(candidates, key=lambda x: x["similarity_score"], reverse=True):
                if c not in balanced_list and len(balanced_list) < max_limit:
                    balanced_list.append(c)
            candidates = balanced_list

        # Step 5: Format selected candidates as SubstituteItem objects
        results: List[SubstituteItem] = []
        for c in candidates[:max_limit]:
            p = c["product"]
            # Clarify the reason based on the strategy applied
            reason = c["reason"]
            if c["is_cross_brand_same_variant"] and strategy == SubstitutionStrategy.SAME_VARIANT_DIFF_BRAND:
                reason = f"Cross-brand alternative: {p['brand']} {p['pack_size']} ({p['stock_cartons']} cartons available)"
            elif c["is_same_brand"] and strategy == SubstitutionStrategy.SAME_BRAND_DIFF_VARIANT:
                reason = f"Same brand variant: {p['name']} ({p['stock_cartons']} cartons available)"

            results.append(
                SubstituteItem(
                    sku_id=c["sku_id"],
                    name=p["name"],
                    brand=p["brand"],
                    pack_size=p["pack_size"],
                    units_per_carton=p["units_per_carton"],
                    wholesale_price_per_carton=p["wholesale_price_per_carton"],
                    mrp_per_unit=p["mrp_per_unit"],
                    stock_cartons=p["stock_cartons"],
                    similarity_score=round(c["similarity_score"], 2),
                    reason=reason
                )
            )

        return results

    def resolve_raw_order(
        self,
        raw_items: List[ExtractedRawItem],
        policy: Optional[SubstitutionPolicy] = None
    ) -> CartSummary:
        """
        Resolves raw items against catalog using the active substitution policy.
        """
        active_policy = policy or self.policy
        resolved_items: List[ResolvedItem] = []
        in_stock_count = 0
        oos_count = 0
        total_amount = 0.0

        for item in raw_items:
            sku_id, conf = self.resolve_sku(item.normalized_name or item.raw_text)

            if not sku_id or sku_id not in self.products:
                resolved_items.append(
                    ResolvedItem(
                        raw_query=item.raw_text,
                        status="NOT_FOUND",
                        requested_cartons=item.quantity,
                        substitutes=[]
                    )
                )
                oos_count += 1
                continue

            prod = self.products[sku_id]
            stock = prod.get("stock_cartons", 0)
            price = prod.get("wholesale_price_per_carton", 0.0)

            if stock >= item.quantity:
                status = "IN_STOCK"
                line_total = price * item.quantity
                in_stock_count += 1
                total_amount += line_total
                substitutes = []
            elif stock > 0:
                status = "PARTIAL_STOCK"
                line_total = price * stock
                in_stock_count += 1
                total_amount += line_total
                substitutes = self.find_substitutes(sku_id, policy=active_policy)
            else:
                status = "OUT_OF_STOCK"
                line_total = 0.0
                oos_count += 1
                substitutes = self.find_substitutes(sku_id, policy=active_policy)

            resolved_items.append(
                ResolvedItem(
                    raw_query=item.raw_text,
                    matched_sku_id=sku_id,
                    matched_name=prod["name"],
                    brand=prod["brand"],
                    category=prod["category"],
                    status=status,
                    requested_cartons=item.quantity,
                    available_cartons=stock,
                    wholesale_price_per_carton=price,
                    line_total=line_total,
                    substitutes=substitutes
                )
            )

        return CartSummary(
            total_requested_items=len(raw_items),
            in_stock_items_count=in_stock_count,
            oos_items_count=oos_count,
            estimated_total_amount=round(total_amount, 2),
            items=resolved_items
        )

    def load_from_json(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Add Product Nodes & Category/Brand Nodes
        for p in data.get("products", []):
            sku_id = p["sku_id"]
            self.products[sku_id] = p
            self.graph.add_node(sku_id, node_type="PRODUCT", **p)

            # Map primary name
            self.alias_map[p["name"].lower().strip()] = sku_id

            # Map aliases
            for alias in p.get("aliases", []):
                self.alias_map[alias.lower().strip()] = sku_id

            # Category & Brand Nodes
            brand_node = f"BRAND_{p['brand'].upper().replace(' ', '_')}"
            cat_node = f"CAT_{p['category'].upper().replace(' ', '_')}"
            subcat_node = f"SUBCAT_{p['subcategory'].upper().replace(' ', '_')}"

            self.graph.add_node(brand_node, node_type="BRAND", name=p["brand"])
            self.graph.add_node(cat_node, node_type="CATEGORY", name=p["category"])
            self.graph.add_node(subcat_node, node_type="SUBCATEGORY", name=p["subcategory"])

            # Edges
            self.graph.add_edge(sku_id, brand_node, rel="BELONGS_TO")
            self.graph.add_edge(sku_id, cat_node, rel="IN_CATEGORY")
            self.graph.add_edge(sku_id, subcat_node, rel="IN_SUBCATEGORY")

        # 2. Add Explicit Substitute Edges
        for sub in data.get("substitute_relations", []):
            src = sub["source_sku"]
            tgt = sub["target_sku"]
            if src in self.products and tgt in self.products:
                self.graph.add_edge(
                    src,
                    tgt,
                    rel="HAS_SUBSTITUTE",
                    sub_type=sub.get("type", "GENERAL"),
                    similarity_score=sub.get("similarity_score", 0.9),
                    reason=sub.get("reason", "Alternative product")
                )

    def resolve_sku(self, query: str) -> Tuple[Optional[str], float]:
        """
        Entity Resolution: Maps raw user query string to canonical SKU ID.
        Uses exact alias match, token overlap, pack size awareness, and fuzzy matching.
        """
        import re

        cleaned = query.lower().strip()
        cleaned_no_punct = re.sub(r"[^a-z0-9\s]", " ", cleaned)
        cleaned_tokens = set(cleaned_no_punct.split())

        # 1. Exact match in alias map
        if cleaned in self.alias_map:
            return self.alias_map[cleaned], 1.0
        if cleaned_no_punct in self.alias_map:
            return self.alias_map[cleaned_no_punct], 1.0

        # Extract pack sizes (e.g. '65g', '130g', '75g', '1l', '100g')
        query_pack_sizes = set(re.findall(r"\b\d+\s*(?:g|gm|ml|l|kg|pouch|rs)\b", cleaned_no_punct))

        best_sku = None
        best_score = 0.0

        for sku_id, prod in self.products.items():
            prod_name_tokens = set(re.sub(r"[^a-z0-9\s]", " ", prod["name"].lower()).split())
            prod_pack = prod.get("pack_size", "").lower().replace(" ", "")

            # Check all aliases for this product
            aliases = [prod["name"].lower()] + [a.lower() for a in prod.get("aliases", [])]
            for alias in aliases:
                alias_clean = re.sub(r"[^a-z0-9\s]", " ", alias)
                alias_tokens = set(alias_clean.split())

                # Overlap ratio
                overlap = len(cleaned_tokens.intersection(alias_tokens))
                total_unique = len(cleaned_tokens.union(alias_tokens))
                if total_unique == 0:
                    continue
                jaccard = overlap / total_unique

                # Substring boost
                if alias in cleaned or cleaned in alias:
                    jaccard = max(jaccard, 0.85)

                # Pack size bonus/penalty
                if query_pack_sizes:
                    if prod_pack in query_pack_sizes:
                        jaccard += 0.2
                    elif any(ps in alias for ps in query_pack_sizes):
                        jaccard += 0.2

                if jaccard > best_score:
                    best_score = jaccard
                    best_sku = sku_id

        if best_sku and best_score >= 0.5:
            return best_sku, round(min(best_score, 1.0), 2)

        # Fallback to difflib close match
        all_candidates = list(self.alias_map.keys())
        matches = difflib.get_close_matches(cleaned, all_candidates, n=1, cutoff=0.55)
        if matches:
            best_match = matches[0]
            similarity = difflib.SequenceMatcher(None, cleaned, best_match).ratio()
            return self.alias_map[best_match], round(similarity, 2)

        return None, 0.0
