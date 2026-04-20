// 1) Top products by purchase count
MATCH (:User)-[r:INTERACTED_WITH]->(p:Product)
RETURN p.product_id AS product_id, sum(r.purchases) AS purchases
ORDER BY purchases DESC
LIMIT 10;

// 2) Users with highest checkout to purchase conversion
MATCH (u:User)-[r:INTERACTED_WITH]->(:Product)
WITH u.user_id AS user_id, sum(r.checkouts) AS checkouts, sum(r.purchases) AS purchases
WHERE checkouts > 0
RETURN user_id, checkouts, purchases, round(toFloat(purchases) / checkouts, 3) AS conversion
ORDER BY conversion DESC, purchases DESC
LIMIT 20;

// 3) Most common next action transitions
MATCH (a1:Action)-[r:NEXT_ACTION]->(a2:Action)
RETURN a1.name AS from_action, a2.name AS to_action, r.count AS count
ORDER BY count DESC
LIMIT 15;

// 4) User event timeline sample
MATCH (u:User {user_id: 'U0001'})-[:PERFORMED]->(e:Event)-[:OF_ACTION]->(a:Action)
MATCH (e)-[:ON_PRODUCT]->(p:Product)
RETURN e.timestamp AS timestamp, a.name AS action, p.product_id AS product_id
ORDER BY timestamp;

// 5) Product touch funnel summary
MATCH (:User)-[r:INTERACTED_WITH]->(p:Product)
RETURN p.product_id AS product_id,
       sum(r.views) AS views,
       sum(r.clicks) AS clicks,
       sum(r.searches) AS searches,
       sum(r.wishlist_adds) AS wishlist_adds,
       sum(r.cart_adds) AS cart_adds,
       sum(r.checkouts) AS checkouts,
       sum(r.purchases) AS purchases
ORDER BY purchases DESC, cart_adds DESC
LIMIT 20;
