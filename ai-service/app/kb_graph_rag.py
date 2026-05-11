import os
import re
import time
import unicodedata

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover
    GraphDatabase = None


TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")
PRODUCT_ID_PATTERN = re.compile(r"\bP\d{4}\b", re.IGNORECASE)

GRAPH_SOURCES = {
    "user_profile": "neo4j:(User)-[INTERACTED_WITH]->(Product)",
    "product_funnel": "neo4j:Product funnel from INTERACTED_WITH counters",
    "trending_products": "neo4j:Global product ranking",
    "action_transition": "neo4j:(Action)-[NEXT_ACTION]->(Action)",
    "time_slot": "neo4j:(Event)-[:IN_TIMESLOT]->(TimeSlot)",
}

STOP_WORDS = {
    "toi",
    "can",
    "muon",
    "cho",
    "ve",
    "la",
    "va",
    "gi",
    "nao",
    "khong",
    "mot",
    "cua",
    "the",
    "how",
    "what",
}

INTENT_KEYWORDS = {
    "action_transition": {"hanh", "vi", "chuoi", "sequence", "next", "buoc", "chuyen", "doi", "transition"},
    "time_slot": {"gio", "khung", "thoi", "diem", "time", "hour", "peak"},
    "product_funnel": {"funnel", "ti", "le", "chuyen", "doi", "checkout", "purchase", "cart"},
    "trending_products": {"top", "hot", "ban", "chay", "pho", "bien", "goi", "y", "trend"},
}


class KBGraphRAG:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "neo4j12345")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

    def _normalize(self, text):
        raw = (text or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", raw)
        return normalized.encode("ascii", "ignore").decode("ascii")

    def _tokenize(self, text):
        return [token for token in TOKEN_PATTERN.findall(self._normalize(text)) if token not in STOP_WORDS]

    def _detect_intent(self, query, customer_id):
        product_match = PRODUCT_ID_PATTERN.search(query or "")
        if product_match:
            return "product_funnel", product_match.group(0).upper()

        tokens = set(self._tokenize(query))
        if customer_id:
            if {"toi", "user", "khach", "hang", "ho", "so", "profile"}.intersection(tokens):
                return "user_profile", None

        for intent, words in INTENT_KEYWORDS.items():
            if words.intersection(tokens):
                return intent, None

        if customer_id:
            return "user_profile", None
        return "trending_products", None

    def _run_query(self, query, **params):
        if GraphDatabase is None:
            raise RuntimeError("Neo4j driver is missing. Please install neo4j package.")

        driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        try:
            with driver.session(database=self.database) as session:
                result = session.run(query, **params)
                return [record.data() for record in result]
        finally:
            driver.close()

    def _retrieve_user_profile(self, customer_id, top_k):
        user_id = f"U{int(customer_id):04d}"
        query = """
        MATCH (u:User {user_id: $user_id})-[r:INTERACTED_WITH]->(p:Product)
        WITH u,
             count(r) AS touched_products,
             sum(r.total_interactions) AS total_events,
             sum(r.purchases) AS purchases,
             sum(r.checkouts) AS checkouts,
             collect({
                product_id: p.product_id,
                total_interactions: r.total_interactions,
                purchases: r.purchases,
                cart_adds: r.cart_adds
             }) AS product_rows
        RETURN u.user_id AS user_id,
               touched_products,
               total_events,
               purchases,
               checkouts,
               product_rows[..$top_k] AS top_products
        """
        return self._run_query(query, user_id=user_id, top_k=top_k)

    def _retrieve_product_funnel(self, product_id, top_k):
        if product_id:
            query = """
            MATCH (:User)-[r:INTERACTED_WITH]->(p:Product {product_id: $product_id})
            RETURN p.product_id AS product_id,
                   sum(r.views) AS views,
                   sum(r.clicks) AS clicks,
                   sum(r.searches) AS searches,
                   sum(r.wishlist_adds) AS wishlist_adds,
                   sum(r.cart_adds) AS cart_adds,
                   sum(r.checkouts) AS checkouts,
                   sum(r.purchases) AS purchases,
                   sum(r.total_interactions) AS total_interactions
            """
            return self._run_query(query, product_id=product_id)

        query = """
        MATCH (:User)-[r:INTERACTED_WITH]->(p:Product)
        RETURN p.product_id AS product_id,
               sum(r.views) AS views,
               sum(r.clicks) AS clicks,
               sum(r.searches) AS searches,
               sum(r.wishlist_adds) AS wishlist_adds,
               sum(r.cart_adds) AS cart_adds,
               sum(r.checkouts) AS checkouts,
               sum(r.purchases) AS purchases,
               sum(r.total_interactions) AS total_interactions
        ORDER BY purchases DESC, checkouts DESC, total_interactions DESC
        LIMIT $top_k
        """
        return self._run_query(query, top_k=top_k)

    def _retrieve_trending_products(self, top_k):
        query = """
        MATCH (:User)-[r:INTERACTED_WITH]->(p:Product)
        RETURN p.product_id AS product_id,
               sum(r.total_interactions) AS total_interactions,
               sum(r.purchases) AS purchases,
               sum(r.checkouts) AS checkouts,
               sum(r.cart_adds) AS cart_adds,
               sum(r.wishlist_adds) AS wishlist_adds
        ORDER BY purchases DESC, cart_adds DESC, total_interactions DESC
        LIMIT $top_k
        """
        return self._run_query(query, top_k=top_k)

    def _retrieve_action_transitions(self, top_k):
        query = """
        MATCH (a1:Action)-[r:NEXT_ACTION]->(a2:Action)
        RETURN a1.name AS from_action, a2.name AS to_action, r.count AS count
        ORDER BY r.count DESC
        LIMIT $top_k
        """
        return self._run_query(query, top_k=top_k)

    def _retrieve_time_slots(self, top_k):
        query = """
        MATCH (e:Event)-[:IN_TIMESLOT]->(t:TimeSlot)
        RETURN t.date AS date, t.hour AS hour, count(e) AS event_count
        ORDER BY event_count DESC
        LIMIT $top_k
        """
        return self._run_query(query, top_k=top_k)

    def retrieve(self, query, customer_id=None, top_k=5):
        started = time.time()
        intent, product_id = self._detect_intent(query, customer_id)

        if top_k <= 0:
            top_k = 5
        top_k = min(top_k, 15)

        try:
            if intent == "user_profile":
                rows = self._retrieve_user_profile(customer_id, top_k)
            elif intent == "product_funnel":
                rows = self._retrieve_product_funnel(product_id, top_k)
            elif intent == "action_transition":
                rows = self._retrieve_action_transitions(top_k)
            elif intent == "time_slot":
                rows = self._retrieve_time_slots(top_k)
            else:
                rows = self._retrieve_trending_products(top_k)

            latency_ms = round((time.time() - started) * 1000, 2)
            return {
                "ok": True,
                "intent": intent,
                "rows": rows,
                "latency_ms": latency_ms,
                "source": GRAPH_SOURCES.get(intent, "neo4j:KB_Graph"),
            }
        except Exception as exc:  # pragma: no cover
            latency_ms = round((time.time() - started) * 1000, 2)
            return {
                "ok": False,
                "intent": intent,
                "rows": [],
                "latency_ms": latency_ms,
                "source": GRAPH_SOURCES.get(intent, "neo4j:KB_Graph"),
                "error": repr(exc),
            }

    def _generate_answer(self, intent, rows):
        if not rows:
            return "Mình chưa truy xuất được dữ liệu từ KB_Graph cho truy vấn này."

        if intent == "user_profile":
            row = rows[0]
            purchases = int(row.get("purchases") or 0)
            checkouts = int(row.get("checkouts") or 0)
            conversion = round((purchases / checkouts), 3) if checkouts > 0 else 0.0
            top_products = row.get("top_products") or []
            top_text = ", ".join(item.get("product_id") for item in top_products[:3] if item.get("product_id"))
            if not top_text:
                top_text = "chưa có sản phẩm nổi bật"
            return (
                f"Theo KB_Graph, hồ sơ user {row.get('user_id')} có {int(row.get('total_events') or 0)} tương tác "
                f"trên {int(row.get('touched_products') or 0)} sản phẩm. "
                f"Checkout={checkouts}, Purchase={purchases}, conversion xấp xỉ {conversion}. "
                f"Top sản phẩm quan tâm: {top_text}."
            )

        if intent == "product_funnel":
            row = rows[0]
            checkouts = int(row.get("checkouts") or 0)
            purchases = int(row.get("purchases") or 0)
            conversion = round((purchases / checkouts), 3) if checkouts > 0 else 0.0
            return (
                f"Funnel cho sản phẩm {row.get('product_id')}: "
                f"view={int(row.get('views') or 0)}, cart_add={int(row.get('cart_adds') or 0)}, "
                f"checkout={checkouts}, purchase={purchases}, conversion checkout->purchase={conversion}."
            )

        if intent == "action_transition":
            top = rows[:3]
            phrase = "; ".join(
                f"{item.get('from_action')} -> {item.get('to_action')} ({int(item.get('count') or 0)})"
                for item in top
            )
            return f"Chuỗi hành vi phổ biến nhất trong KB_Graph: {phrase}."

        if intent == "time_slot":
            top = rows[:3]
            phrase = "; ".join(
                f"{item.get('date')} {str(item.get('hour')).zfill(2)}h ({int(item.get('event_count') or 0)} events)"
                for item in top
            )
            return f"Khung giờ tương tác cao từ KB_Graph: {phrase}."

        top = rows[:3]
        phrase = ", ".join(
            f"{item.get('product_id')} (purchase={int(item.get('purchases') or 0)})" for item in top
        )
        return f"Top sản phẩm nổi bật theo KB_Graph hiện tại: {phrase}."

    def ask(self, query, customer_id=None, top_k=5):
        retrieval = self.retrieve(query=query, customer_id=customer_id, top_k=top_k)
        rows = retrieval.get("rows") or []
        answer = self._generate_answer(retrieval.get("intent"), rows)

        ok = bool(retrieval.get("ok", False)) and bool(rows)
        error = retrieval.get("error")
        if retrieval.get("ok", False) and not rows:
            ok = False
            error = error or "KB_Graph hiện chưa có dữ liệu phù hợp cho truy vấn này."

        citations = [
            {
                "type": "graph",
                "source": retrieval.get("source", "neo4j:KB_Graph"),
                "rows": len(rows),
            }
        ]

        confidence = 0.75 if ok else 0.45

        return {
            "ok": ok,
            "intent": retrieval.get("intent"),
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
            "graph_context": rows,
            "latency_ms": retrieval.get("latency_ms", 0.0),
            "error": error,
        }
