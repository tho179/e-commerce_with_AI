// KB_Graph constraints
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE;
CREATE CONSTRAINT product_id_unique IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE;
CREATE CONSTRAINT action_name_unique IF NOT EXISTS FOR (a:Action) REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE;
CREATE CONSTRAINT timeslot_key_unique IF NOT EXISTS FOR (t:TimeSlot) REQUIRE t.key IS UNIQUE;
CREATE CONSTRAINT kbgraph_name_unique IF NOT EXISTS FOR (k:KBGraph) REQUIRE k.name IS UNIQUE;
