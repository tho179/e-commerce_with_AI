# KB_Graph with Neo4j

This folder builds a Neo4j knowledge graph named KB_Graph from data_user500.csv.

## 1) Graph model

### Node labels
- User: user profile by user_id
- Product: product profile by product_id
- Action: action taxonomy (view, click, search, add_to_wishlist, add_to_cart, remove_from_cart, checkout, purchase)
- Event: one interaction event per CSV row
- TimeSlot: normalized time bucket by date and hour
- KBGraph: metadata node for the imported graph

### Relationship types
- (User)-[:PERFORMED]->(Event)
- (Event)-[:OF_ACTION]->(Action)
- (Event)-[:ON_PRODUCT]->(Product)
- (Event)-[:IN_TIMESLOT]->(TimeSlot)
- (User)-[:INTERACTED_WITH]->(Product) with aggregated action counters
- (Action)-[:NEXT_ACTION]->(Action) with transition count

## 2) Files
- build_kb_graph.py: end-to-end import script
- neo4j_schema.cypher: constraints and schema baseline
- sample_queries.cypher: ready-to-run analytics queries
- docker-compose.neo4j.yml: standalone Neo4j service for this KB graph
- requirements-kb.txt: Python dependencies for graph import

## 3) Start Neo4j
Run from repository root:

```powershell
cd kb_graph
docker compose -f docker-compose.neo4j.yml up -d
```

Neo4j Browser URL: http://localhost:7474
- username: neo4j
- password: neo4j12345

## 4) Install dependencies
Run from repository root:

```powershell
python -m pip install -r kb_graph/requirements-kb.txt
```

## 5) Build KB_Graph
Run from repository root:

```powershell
python kb_graph/build_kb_graph.py --csv data_user500.csv --reset
```

Optional dry run (no DB write):

```powershell
python kb_graph/build_kb_graph.py --csv data_user500.csv --dry-run
```

## 6) Explore graph
Open Neo4j Browser and run queries from sample_queries.cypher.

## 7) RAG chat endpoint (aiservice)
After KB_Graph is built, start aiservice and call the graph-based RAG endpoint:

```powershell
curl -X POST http://localhost:8021/chat/rag/graph/ \
	-H "Content-Type: application/json" \
	-H "X-Service-Token: bookstore-internal-token" \
	-d '{"query":"top san pham ban chay", "customer_id": 1, "top_k": 5}'
```

Expected response fields:
- intent: graph intent detected from query
- answer: grounded answer generated from KB_Graph facts
- citations: graph source citation
- graph_context: raw retrieved rows for auditability
- products: compact product suggestions derived from graph rows
- recommendations: personalized recommendation fallback from aiservice

## 8) Notes
- Use --reset to remove only managed labels before rebuilding.
- If your Neo4j credentials differ, pass --uri, --user, --password, --database.
