import pandas as pd

from helpers import cleanup_string

TYPES_MAP = {}
NODE_METADATA = {}
DESCRIPTIONS_MAP = {}
NAMES_MAP = {
    # Our errors
    "E2": "E2 Interface",
    # Our preference
    "xApps": "Near-RT RIC",
    "xAPPs": "Near-RT RIC",
    "rApps": "Non-RT RIC",
    "rAPPs": "Non-RT RIC",
    "ASSET-C-29": "O-Cloud",
    "ASSET-C-30": "External Components",
    "ASSET-C-08": "O-Cloud",
    "NFO/FOCOM": "O-Cloud",
    "Database holding data from xApp applications and E2 Node": "Near-RT RIC",
    "Database holding data from xApp applications and E2": "Near-RT RIC",
    "ML components deploying machine learning (xApps/rApps)": "O-Cloud",
    "Training or test data sets collected externally or internally": "External Components",
    "Trained ML model": "External Components",
    "Near-RT-RIC SW": "Near-RT RIC",
    "Non-RT-RIC SW": "Non-RT RIC",
    "O1 interface for streaming data": "O1 Interface",
    "E2 interface for streaming data": "E2 Interface",
    "ML prediction results": "External Components",
    "A1 policies": "A1 Interface",
    "E2 node data": "Near-RT RIC",
    "Data transported over the O1 interface": "O1 Interface",
    "AAL software": "O-Cloud",
    "Hardware accelerator device firmware": "External Components",
    # Their inconsistencies
    "Non-RT-RIC": "Non-RT RIC",
    "airlink with UE": "Airlink",
    "E2 Functions": "E2 Interface",
    "Y1 Functions": "Y1 Interface",
    "SMO Framework": "SMO",
    "R1 interface": "R1 Interface",
    "A1 interface": "A1 Interface",
    "Apps/VNFs/CNFs": "SMO",
    "Apps/VNFs/CNFs images": "SMO",
    "O2": "O2 Interface",
}
DROP_COMPONENTS = []
EXPANSIONS = {}
QUERIES = []
RELATIONSHIPS = {}


def expand_relationship(
    df: pd.DataFrame,
    src: str,
    dst: str,
    relationship: str,
    expansion: list,
    reverse: bool = False,
):
    """
    Register a relationship between two nodes.
    """

    return [
        (row[src], row[dst], relationship, expansion, reverse)
        for _, row in df.iterrows()
    ]


def record_relationship(src_type: str, dst_type: str, relationship_type: str):
    """
    Store a mapping for schema purposes
    """
    dsts = RELATIONSHIPS.get(src_type, set())
    dsts.add(f"--{relationship_type}--> {dst_type}")
    RELATIONSHIPS[src_type] = dsts


def get_expansions(component):
    """
    Get expansions for a specific component
    """

    return EXPANSIONS.get(component, [component])


def set_node_metadata(nodes: list, tag: str, metadata_list: list):
    """
    Set metadata for a specific node
    """

    if len(nodes) != len(metadata_list):
        raise ValueError("Nodes and metadata must be the same length")

    for node, metadata in zip(nodes, metadata_list):
        data = NODE_METADATA.get(node, {})

        if metadata in data:
            raise ValueError(f"Metadata for node {node} already set")

        data[tag] = metadata
        NODE_METADATA[node] = data


def get_node_metadata(node: str):
    """
    Get metadata for a specific node
    """

    return NODE_METADATA.get(node)


def drop_component(item: str):
    """
    Drop an item from the map
    """

    if item in DROP_COMPONENTS:
        return True

    return False


def register_nodes(
    df: pd.DataFrame, key_col: str, component_type: str, metadata_cols: list = None
):
    """
    Map a list of components to a specific component type.

    No duplicate names allowed.
    """
    for idx, row in df.iterrows():
        component = row[key_col]
        metadata = {col: row[col] for col in metadata_cols} if metadata_cols else {}

        if component in TYPES_MAP:
            raise ValueError(
                f'Component "{component}" already registered! ({component_type} vs {TYPES_MAP[component]})'
            )

        if metadata:
            NODE_METADATA[component] = metadata

        # Map component to a specific component type
        TYPES_MAP[component] = component_type


def get_registered_nodes() -> list:
    return list(TYPES_MAP.keys())


def resolve_name_map(name: str) -> str:
    """
    Maps a source name to a true name for deduplication purposes
    """

    real_name = NAMES_MAP.get(name)

    if not real_name:
        return name

    return real_name


def resolve_name_to_type(name: str) -> str:
    """
    Maps an arbitrary name to a specific node type

    This helps us enforce that every relationship is actually created.
    """

    component_type = TYPES_MAP.get(name)

    if not component_type:
        raise ValueError(f'Component "{name}" not found in component map')

    return component_type


def get_nodes_pseudocode() -> str:
    """
    Returns a pseudocode representation of node types and their metadata schema
    """
    output = ["Nodes:"]

    # Get all unique node types
    node_types = set(TYPES_MAP.values())

    for node_type in sorted(node_types):
        output.append(f"  {node_type}:")

        # Find all nodes of this type
        nodes_of_type = [
            node for node, type_val in TYPES_MAP.items() if type_val == node_type
        ]

        # Pick first node as example
        example_node = nodes_of_type[0] if nodes_of_type else None

        # Collect all metadata keys for this node type
        metadata_keys = set()
        for node in nodes_of_type:
            metadata = NODE_METADATA.get(node, {})
            metadata_keys.update(metadata.keys())

        # Always include the name property
        output.append("    Properties:")
        output.append(
            f"      name: string (example: '{example_node}')"
        )  # All nodes have a name

        # Add all other metadata properties
        for key in sorted(metadata_keys):
            # Collect all unique values for this property across nodes of this type
            unique_values = set()
            for node in nodes_of_type:
                metadata = NODE_METADATA.get(node, {})
                if key in metadata and metadata[key] is not None:
                    unique_values.add(str(metadata[key]))

            # If there are fewer than 5 unique values, display all of them
            if len(unique_values) < 5:
                values_str = ", ".join(
                    [
                        f"'{val[:47] + '...' if isinstance(val, str) and len(val) > 50 else val}'"
                        for val in sorted(unique_values)
                    ]
                )
                cleaned_key = cleanup_string(key)
                output.append(f"      {cleaned_key}: values: [{values_str}]")
            else:
                # Get example value from the first node that has this metadata key
                for node in nodes_of_type:
                    metadata = NODE_METADATA.get(node, {})
                    if key in metadata and metadata[key] is not None:
                        example_value = str(metadata[key]).replace("\n", " ")
                        if len(example_value) > 50:
                            example_value = example_value[:47] + "..."
                        cleaned_key = cleanup_string(key)
                        output.append(
                            f"      {cleaned_key}: (example: '{example_value}')"
                        )
                        break

    return "\n".join(output)


def get_relationships_pseudocode() -> str:
    """
    Returns a pseudocode representation of relationships between components
    """
    output = ["Relationships:"]

    # Sort relationships for consistent output
    for src_type in sorted(RELATIONSHIPS.keys()):
        # Sort destination types for consistent output
        for dst_type in sorted(RELATIONSHIPS[src_type]):
            output.append(f"    {src_type} {dst_type}")

    return "\n".join(output)
