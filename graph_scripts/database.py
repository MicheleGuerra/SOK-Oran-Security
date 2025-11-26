from neo4j import GraphDatabase

LOCAL = True

# Connect to Neo4j database

if LOCAL:
    # local db config
    # uri = "bolt://127.0.0.1:7689"  # Adjust if necessary (e.g., add IP or port)
    uri = "neo4j://127.0.0.1:7687"  # Adjust if necessary (e.g., add IP or port)
    username = "neo4j"
    password = "securesecure"

else:
    uri = "neo4j://127.0.0.1:7687"  # Adjust if necessary (e.g., add IP or port)
    username = "neo4j"
    password = "securesecure"

driver = GraphDatabase.driver(uri, auth=(username, password))


def drop_all_data(driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def insert_row(tx, component_name, row: dict):
    """
    Inserts a row dict into the GraphQL database
    """
    for key in row.keys():
        if "-" in key:
            raise ValueError(
                f"Keys in the row dict should not contain hyphens. Found key: {key}"
            )

    query = (
        f"CREATE (c:{component_name} "
        + "{"
        + ", ".join([f"{key}: ${key}" for key in row.keys()])
        + "})"
    )
    print(f"Inserting {component_name}: {query} ({row})")

    tx.run(query, **row)


def create_relationship(
    tx,
    node1_type,
    node1_id_name,
    node1_id,
    node2_type,
    node2_id_name,
    node2_id,
    relationship_type,
    metadata={},
):
    """
    Finds two nodes by their IDs and creates a relationship between them.

    Example:
    ```
    session.write_transaction(create_relationship, 'Person', 'Movie', 123, 456, 'LIKES')
    ```
    """
    metadata_str = ", ".join([f"{key}: ${key}" for key in metadata.keys()])

    query = (
        f"MATCH (a:{node1_type} "
        + "{"
        + f"{node1_id_name}: $id1"
        + "}"
        + f"), (b:{node2_type} "
        + "{"
        + f"{node2_id_name}: $id2"
        + "}) "
        f"CREATE (a)-[r:{relationship_type}  {{{metadata_str}}}]->(b)"
    )

    print(
        f"Creating relationship: {node1_type}({node1_id})-[{relationship_type}]->{node2_type}({node2_id})"
    )
    print(f"Using query: {query}")

    tx.run(query, id1=node1_id, id2=node2_id, **metadata)
