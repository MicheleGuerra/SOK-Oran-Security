#!/usr/bin/env python

import time

import pandas as pd

from mapping import *
from helpers import cleanup_key_names
from database import driver, insert_row, create_relationship
from drop_database import drop_all_data

from parsers.components import df as components_df
from parsers.interfaces import df as interfaces_df
from parsers.software import df as software_df
from parsers.cves import df as cves_df
from parsers.cwes import df as cwes_df
from parsers.threats import df as threats_df
from parsers.academic import df_attacks, df_defenses, df_preventative, df_our_attacks
from parsers.government import df as government_df


DRY_RUN = False


if __name__ == "__main__":
    # Clean previous data
    if not DRY_RUN:
        print("Drop all data from the database!")
        drop_all_data(driver)
        print("Done!")

    """
    Stage 1 - Abstract Components and Interfaces
    """

    # Map components to their respective types (and check for duplicates)
    register_nodes(components_df, key_col="Component", component_type="Component")
    register_nodes(interfaces_df, key_col="Interface", component_type="Interface")
    register_nodes(
        software_df,
        key_col="Project",
        component_type="Software",
        metadata_cols=["Description", "Sponsor", "Publisher"],
    )
    register_nodes(
        cves_df,
        key_col="CVE ID",
        component_type="CVE",
        metadata_cols=[
            "Description",
            "Date Published",
            "URL",
            "CVSS (V3.1)",
            "CWEs",
            "Public",
            "Reference",
            "Attribution",
        ],
    )
    register_nodes(
        cwes_df, key_col="CWE ID", component_type="CWE", metadata_cols=["Description"]
    )
    register_nodes(
        threats_df,
        key_col="Risk ID",
        component_type="Threat",
        metadata_cols=list(threats_df.columns[1:]),
    )
    register_nodes(
        df_attacks, key_col="Name", component_type="Attack", metadata_cols=["Reference"]
    )
    register_nodes(
        df_our_attacks,
        key_col="Name",
        component_type="OurAttack",
        metadata_cols=["Reference"],
    )
    register_nodes(
        df_defenses,
        key_col="Name",
        component_type="Defense",
        metadata_cols=["Reference"],
    )
    register_nodes(
        df_preventative,
        key_col="Name",
        component_type="PreventiveMeasure",
        metadata_cols=["Reference"],
    )
    register_nodes(
        government_df,
        key_col="Name",
        component_type="GovernmentThreat",
        metadata_cols=["Description", "Ecosystem", "Source", "Spec. Issue"],
    )

    # Create these nodes
    all_nodes = get_registered_nodes()

    # All components list for expansions
    all_components = list(components_df["Component"])
    all_interfaces = list(interfaces_df["Interface"])

    # Create all relationships
    all_relationships = [
        # Map: Interfaces <-> {Components}
        *expand_relationship(interfaces_df, "Interface", "Connects", "CONNECTS", None),
        # Map: Software <-> {Components}
        *expand_relationship(software_df, "Project", "Components", "IMPLEMENTS", None),
        # Map: CVEs <-> {Software}
        *expand_relationship(cves_df, "CVE ID", "Software", "AFFECTS", None),
        # Map: CWEs <-> {CVEs}
        *expand_relationship(cves_df, "CVE ID", "CWEs", "ASSOCIATED_WITH", None),
        # Map: Threats <-> {Components,Interfaces}
        *expand_relationship(
            threats_df,
            "Risk ID",
            "Affected Components",
            "TARGETS",
            expansion=all_components,
        ),
        # Map: Extra Threats <-> {Components,Interfaces}
        *expand_relationship(
            threats_df, "Risk ID", "Extra Interfaces", "TARGETS", None
        ),
        # Map: Attacks <-> {Components,Interfaces}
        *expand_relationship(
            df_attacks,
            "Name",
            "Target Components / Interfaces",
            "TARGETS",
            expansion=all_components,
        ),
        # Map: OurAttacks <-> {Components,Interfaces}
        *expand_relationship(
            df_our_attacks,
            "Name",
            "Target Components / Interfaces",
            "TARGETS",
            expansion=all_components,
        ),
        # Map: Defenses <-> {Components,Interfaces}
        *expand_relationship(
            df_defenses,
            "Name",
            "Target Components / Interfaces",
            "SECURES",
            expansion=all_components,
        ),
        # Map: Preventive Measures <-> {Components,Interfaces}
        *expand_relationship(
            df_preventative,
            "Name",
            "Target Components / Interfaces",
            "SECURES",
            expansion=all_components,
        ),
        # Map: Government Threats <-> {Components,Interfaces}
        *expand_relationship(
            government_df, "Name", "Components", "TARGETS", expansion=all_components
        ),
        *expand_relationship(
            government_df, "Name", "Interfaces", "TARGETS", expansion=all_interfaces
        ),
    ]

    # Check for duplicates (just in case)
    if len(all_nodes) != len(set(all_nodes)):
        raise ValueError("Duplicate nodes found")

    # Create nodes
    with driver.session() as session:
        for node in all_nodes:
            node_type = resolve_name_to_type(node)
            node_metadata = get_node_metadata(node)
            node_metadata = cleanup_key_names(node_metadata) if node_metadata else {}

            row = {
                "name": node,
            }

            if node_metadata:
                row.update(node_metadata)

            if not DRY_RUN:
                session.execute_write(insert_row, node_type, row)

    with driver.session() as session:
        for (
            node,
            relationships,
            relationship_name,
            expansion,
            reverse,
        ) in all_relationships:
            node = resolve_name_map(node)
            node_type = resolve_name_to_type(node)

            if pd.isna(relationships):
                continue

            relationships = [r.strip() for r in relationships.split(", ")]
            relationship_metadata = {"all": False}

            # Expand "All" to all relevant components (and mark metadata on relationship)
            if len(relationships) == 1 and relationships[0].lower() == "all":
                relationships = expansion
                relationship_metadata["all"] = True

            # Expand component relationships (i.e. O-CU -> O-CU-CP, O-CU-UP)
            relationships = [
                item for sublist in relationships for item in get_expansions(sublist)
            ]

            # Map every relationship
            mapped_nodes = []
            for destination_node in relationships:
                # Skip items on the drop list
                if drop_component(destination_node):
                    continue

                # Fix destination node name if necessary
                destination_node = resolve_name_map(destination_node)

                # Skip if mapping resolves to something we already added
                if destination_node in mapped_nodes:
                    continue

                mapped_nodes.append(destination_node)

                # Get destination node type
                destination_node_type = resolve_name_to_type(destination_node)

                src_node, src_node_type = node, node_type
                dest_node, dest_node_type = destination_node, destination_node_type

                # Allow for reverse relationships
                if reverse:
                    src_node, dest_node = dest_node, src_node
                    src_node_type, dest_node_type = dest_node_type, src_node_type

                record_relationship(src_node_type, dest_node_type, relationship_name)

                # Create relationship
                if not DRY_RUN:
                    session.execute_write(
                        create_relationship,
                        src_node_type,
                        "name",
                        src_node,
                        dest_node_type,
                        "name",
                        dest_node,
                        relationship_name,
                        relationship_metadata,
                    )

    for query in QUERIES:
        with driver.session() as session:
            print(f"Running query: {query}")
            start = time.time()
            session.run(query)
            end = time.time()
            print(f"Query took {end - start:.2f}s")

    # Print unique node types and relationships
    print(get_nodes_pseudocode())
    print()
    print(get_relationships_pseudocode())

    driver.close()
