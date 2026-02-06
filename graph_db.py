import kuzu
from config import Config
from logger import get_logger

logger = get_logger(__name__)


class GraphDB:
    def __init__(self, config: Config, read_only: bool = False):
        self.db = kuzu.Database(config.graph_db_path(), read_only=read_only)
        self.conn = kuzu.Connection(self.db)
        if not read_only:
            self._setup_schema()

    def _setup_schema(self):
        try:
            self.conn.execute(
                "CREATE NODE TABLE Entity(name STRING, label STRING, PRIMARY KEY (name))"
            )
            logger.info("Created NODE TABLE Entity")
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.error(f"Error creating Entity table: {e}")

        try:
            self.conn.execute(
                "CREATE REL TABLE RelatedTo(FROM Entity TO Entity, relation STRING)"
            )
            logger.info("Created REL TABLE RelatedTo")
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.error(f"Error creating RelatedTo table: {e}")

    def update_graph(self, entities: dict):
        """
        Updates the graph with nodes and edges from entities.
        entities: {
            "nodes": [{"id": "Name", "label": "Type"}],
            "edges": [{"source": "A", "target": "B", "relation": "REL"}]
        }
        """
        nodes = entities.get("nodes", [])
        edges = entities.get("edges", [])

        # Upsert nodes
        for node in nodes:
            node_id = node.get("id")
            label = node.get("label", "Unknown")
            if not node_id:
                continue

            try:
                # Kuzu doesn't have a native UPSERT for nodes in all versions,
                # but we can try to MATCH and then CREATE if not exists,
                # or just try CREATE and ignore if exists.
                # For simplicity, we'll use a MERGE-like approach if supported,
                # or just use simple logic.
                # In current Kuzu, we can use:
                self.conn.execute(
                    "MERGE (e:Entity {name: $name}) ON CREATE SET e.label = $label ON MATCH SET e.label = $label",
                    {"name": node_id, "label": label},
                )
            except Exception as e:
                logger.error(f"Error upserting node {node_id}: {e}")

        # Insert edges
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            relation = edge.get("relation", "RELATED_TO")

            if not source or not target:
                continue

            try:
                # For edges, we can also use MERGE to avoid duplicates
                self.conn.execute(
                    "MATCH (s:Entity {name: $source}), (t:Entity {name: $target}) "
                    "MERGE (s)-[r:RelatedTo {relation: $relation}]->(t)",
                    {"source": source, "target": target, "relation": relation},
                )
            except Exception as e:
                logger.error(f"Error creating edge {source} -> {target}: {e}")

    def list_entities(self, label: str = None):
        """
        Lists all entities in the database, optionally filtered by label.
        """
        if label:
            query = "MATCH (e:Entity {label: $label}) RETURN e.name, e.label"
            params = {"label": label}
        else:
            query = "MATCH (e:Entity) RETURN e.name, e.label"
            params = {}

        try:
            result = self.conn.execute(query, params)
            entities = []
            while result.has_next():
                row = result.get_next()
                entities.append({"name": row[0], "label": row[1]})
            return entities
        except Exception as e:
            logger.error(f"Error listing entities: {e}")
            return []

    def list_relations(self, entity_name: str, relation_type: str = None):
        """
        Lists all relations for a given entity, optionally filtered by relation type.
        """
        if relation_type:
            query = (
                "MATCH (s:Entity {name: $name})-[r:RelatedTo {relation: $relation}]->(t:Entity) "
                "RETURN s.name, r.relation, t.name"
            )
            params = {"name": entity_name, "relation": relation_type}
        else:
            query = (
                "MATCH (s:Entity {name: $name})-[r:RelatedTo]->(t:Entity) "
                "RETURN s.name, r.relation, t.name"
            )
            params = {"name": entity_name}

        try:
            result = self.conn.execute(query, params)
            relations = []
            while result.has_next():
                row = result.get_next()
                relations.append(
                    {"source": row[0], "relation": row[1], "target": row[2]}
                )
            return relations
        except Exception as e:
            logger.error(f"Error listing relations for {entity_name}: {e}")
            return []
