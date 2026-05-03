from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover
    GraphDatabase = None


ACTION_TO_PROPERTY = {
    "view": "views",
    "click": "clicks",
    "search": "searches",
    "add_to_wishlist": "wishlist_adds",
    "add_to_cart": "cart_adds",
    "remove_from_cart": "cart_removes",
    "checkout": "checkouts",
    "purchase": "purchases",
}

MANAGED_LABELS = ["User", "Product", "Action", "Event", "TimeSlot", "KBGraph"]

SCHEMA_QUERIES = [
    "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
    "CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
    "CREATE CONSTRAINT action_name_unique IF NOT EXISTS FOR (a:Action) REQUIRE a.name IS UNIQUE",
    "CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
    "CREATE CONSTRAINT timeslot_key_unique IF NOT EXISTS FOR (t:TimeSlot) REQUIRE t.key IS UNIQUE",
    "CREATE CONSTRAINT kbgraph_name_unique IF NOT EXISTS FOR (k:KBGraph) REQUIRE k.name IS UNIQUE",
]

DELETE_MANAGED_NODES_QUERY = """
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN $labels)
DETACH DELETE n
"""

MERGE_ACTIONS_QUERY = """
UNWIND $rows AS row
MERGE (:Action {name: row.name})
"""

MERGE_EVENTS_QUERY = """
UNWIND $rows AS row
MERGE (u:User {user_id: row.user_id})
MERGE (p:Product {product_id: row.product_id})
MERGE (a:Action {name: row.action})
MERGE (t:TimeSlot {key: row.time_key})
  ON CREATE SET t.date = row.date, t.hour = row.hour, t.day_of_week = row.day_of_week
MERGE (e:Event {event_id: row.event_id})
SET e.timestamp = row.timestamp
MERGE (u)-[:PERFORMED]->(e)
MERGE (e)-[:OF_ACTION]->(a)
MERGE (e)-[:ON_PRODUCT]->(p)
MERGE (e)-[:IN_TIMESLOT]->(t)
"""

CLEAR_INTERACTIONS_QUERY = "MATCH (:User)-[r:INTERACTED_WITH]->(:Product) DELETE r"

MERGE_INTERACTIONS_QUERY = """
UNWIND $rows AS row
MATCH (u:User {user_id: row.user_id})
MATCH (p:Product {product_id: row.product_id})
MERGE (u)-[r:INTERACTED_WITH]->(p)
SET r.total_interactions = row.total_interactions,
    r.first_timestamp = row.first_timestamp,
    r.last_timestamp = row.last_timestamp,
    r.views = row.views,
    r.clicks = row.clicks,
    r.searches = row.searches,
    r.wishlist_adds = row.wishlist_adds,
    r.cart_adds = row.cart_adds,
    r.cart_removes = row.cart_removes,
    r.checkouts = row.checkouts,
    r.purchases = row.purchases
"""

CLEAR_TRANSITIONS_QUERY = "MATCH (:Action)-[r:NEXT_ACTION]->(:Action) DELETE r"

MERGE_TRANSITIONS_QUERY = """
UNWIND $rows AS row
MATCH (a1:Action {name: row.from_action})
MATCH (a2:Action {name: row.to_action})
MERGE (a1)-[r:NEXT_ACTION]->(a2)
SET r.count = row.count
"""

MERGE_GRAPH_METADATA_QUERY = """
MERGE (k:KBGraph {name: 'KB_Graph'})
SET k.source_file = $source_file,
    k.total_events = $total_events,
    k.total_users = $total_users,
    k.total_products = $total_products,
    k.total_actions = $total_actions,
    k.total_transitions = $total_transitions,
    k.updated_at = datetime()
"""


def chunk_rows(rows: List[Dict], chunk_size: int) -> Iterable[List[Dict]]:
    for start in range(0, len(rows), chunk_size):
        yield rows[start : start + chunk_size]


def load_csv(csv_path: Path) -> pd.DataFrame:
    required_columns = {"user_id", "product_id", "action", "timestamp"}
    df = pd.read_csv(csv_path)
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df[["user_id", "product_id", "action", "timestamp"]].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    ts = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = ts.dt.strftime("%Y-%m-%d")
    df["hour"] = ts.dt.hour.astype(int)
    df["day_of_week"] = ts.dt.day_name()
    df["time_key"] = df["date"] + "_" + df["hour"].astype(str).str.zfill(2)
    df["event_id"] = [f"E{i:07d}" for i in range(1, len(df) + 1)]

    unknown_actions = set(df["action"].unique()).difference(ACTION_TO_PROPERTY)
    if unknown_actions:
        raise ValueError(f"Unsupported action values: {sorted(unknown_actions)}")

    return df


def build_event_rows(df: pd.DataFrame) -> List[Dict]:
    columns = [
        "event_id",
        "user_id",
        "product_id",
        "action",
        "timestamp",
        "date",
        "hour",
        "day_of_week",
        "time_key",
    ]
    return df[columns].to_dict("records")


def build_interaction_rows(df: pd.DataFrame) -> List[Dict]:
    base = (
        df.groupby(["user_id", "product_id"])
        .agg(
            total_interactions=("event_id", "count"),
            first_timestamp=("timestamp", "min"),
            last_timestamp=("timestamp", "max"),
        )
        .reset_index()
    )

    action_counts = (
        df.groupby(["user_id", "product_id", "action"])["event_id"]
        .count()
        .unstack(fill_value=0)
        .reset_index()
    )

    merged = base.merge(action_counts, on=["user_id", "product_id"], how="left")

    for action_name, property_name in ACTION_TO_PROPERTY.items():
        if action_name not in merged.columns:
            merged[action_name] = 0
        merged[property_name] = merged[action_name].astype(int)

    keep_columns = [
        "user_id",
        "product_id",
        "total_interactions",
        "first_timestamp",
        "last_timestamp",
        "views",
        "clicks",
        "searches",
        "wishlist_adds",
        "cart_adds",
        "cart_removes",
        "checkouts",
        "purchases",
    ]

    return merged[keep_columns].to_dict("records")


def build_transition_rows(df: pd.DataFrame) -> List[Dict]:
    transitions = df[["user_id", "timestamp", "action"]].copy()
    transitions = transitions.sort_values(["user_id", "timestamp"])  # deterministic per user
    transitions["next_action"] = transitions.groupby("user_id")["action"].shift(-1)
    transitions = transitions.dropna(subset=["next_action"])

    grouped = (
        transitions.groupby(["action", "next_action"])  # from -> to
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    grouped = grouped.rename(columns={"action": "from_action", "next_action": "to_action"})
    return grouped.to_dict("records")


def print_data_summary(df: pd.DataFrame) -> None:
    print("Data summary")
    print(f"- total events: {len(df)}")
    print(f"- total users: {df['user_id'].nunique()}")
    print(f"- total products: {df['product_id'].nunique()}")
    print(f"- action classes: {df['action'].nunique()}")


def run_graph_import(
    uri: str,
    user: str,
    password: str,
    database: str,
    event_rows: List[Dict],
    interaction_rows: List[Dict],
    transition_rows: List[Dict],
    source_file: str,
    total_users: int,
    total_products: int,
    total_actions: int,
    batch_size: int,
    reset: bool,
) -> None:
    if GraphDatabase is None:
        raise RuntimeError(
            "Neo4j Python driver is not installed. Install dependencies from kb_graph/requirements-kb.txt"
        )

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            for query in SCHEMA_QUERIES:
                session.run(query).consume()

            if reset:
                session.run(DELETE_MANAGED_NODES_QUERY, labels=MANAGED_LABELS).consume()

            action_rows = [{"name": action} for action in sorted(ACTION_TO_PROPERTY.keys())]
            session.run(MERGE_ACTIONS_QUERY, rows=action_rows).consume()

            for batch in chunk_rows(event_rows, batch_size):
                session.run(MERGE_EVENTS_QUERY, rows=batch).consume()

            session.run(CLEAR_INTERACTIONS_QUERY).consume()
            for batch in chunk_rows(interaction_rows, batch_size):
                session.run(MERGE_INTERACTIONS_QUERY, rows=batch).consume()

            session.run(CLEAR_TRANSITIONS_QUERY).consume()
            for batch in chunk_rows(transition_rows, batch_size):
                session.run(MERGE_TRANSITIONS_QUERY, rows=batch).consume()

            session.run(
                MERGE_GRAPH_METADATA_QUERY,
                source_file=source_file,
                total_events=len(event_rows),
                total_users=total_users,
                total_products=total_products,
                total_actions=total_actions,
                total_transitions=len(transition_rows),
            ).consume()

            counts = {
                "users": session.run("MATCH (n:User) RETURN count(n) AS c").single()["c"],
                "products": session.run("MATCH (n:Product) RETURN count(n) AS c").single()["c"],
                "events": session.run("MATCH (n:Event) RETURN count(n) AS c").single()["c"],
                "interactions": session.run(
                    "MATCH (:User)-[r:INTERACTED_WITH]->(:Product) RETURN count(r) AS c"
                ).single()["c"],
                "transitions": session.run(
                    "MATCH (:Action)-[r:NEXT_ACTION]->(:Action) RETURN count(r) AS c"
                ).single()["c"],
            }

            print("Neo4j import completed")
            print(f"- users: {counts['users']}")
            print(f"- products: {counts['products']}")
            print(f"- events: {counts['events']}")
            print(f"- user-product interactions: {counts['interactions']}")
            print(f"- action transitions: {counts['transitions']}")
    finally:
        driver.close()


def parse_args() -> argparse.Namespace:
    default_csv = Path(__file__).resolve().parents[1] / "data" / "data_user500.csv"
    parser = argparse.ArgumentParser(description="Build KB_Graph in Neo4j from user behavior CSV")
    parser.add_argument("--csv", default=str(default_csv), help="Path to CSV file")
    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j bolt URI")
    parser.add_argument("--user", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", default="neo4j12345", help="Neo4j password")
    parser.add_argument("--database", default="neo4j", help="Neo4j database name")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for import")
    parser.add_argument("--reset", action="store_true", help="Delete previously managed KB_Graph labels")
    parser.add_argument("--dry-run", action="store_true", help="Prepare data only and skip Neo4j import")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv).resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = load_csv(csv_path)
    print_data_summary(df)

    event_rows = build_event_rows(df)
    interaction_rows = build_interaction_rows(df)
    transition_rows = build_transition_rows(df)

    print(f"- prepared event rows: {len(event_rows)}")
    print(f"- prepared interaction rows: {len(interaction_rows)}")
    print(f"- prepared transition rows: {len(transition_rows)}")

    if args.dry_run:
        print("Dry-run mode enabled. Neo4j import skipped.")
        return

    run_graph_import(
        uri=args.uri,
        user=args.user,
        password=args.password,
        database=args.database,
        event_rows=event_rows,
        interaction_rows=interaction_rows,
        transition_rows=transition_rows,
        source_file=str(csv_path),
        total_users=df["user_id"].nunique(),
        total_products=df["product_id"].nunique(),
        total_actions=df["action"].nunique(),
        batch_size=args.batch_size,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
