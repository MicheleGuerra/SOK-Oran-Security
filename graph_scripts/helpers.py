def cleanup_string(s: str):
    """
    Strip out special characters and spaces from strings
    """
    return (
        s.lower()
        .replace(" ", "_")
        .replace(":", "")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "_")
    )


def cleanup_key_names(d: dict):
    """
    Strip out special characters and spaces from dictionary keys
    """
    return {cleanup_string(k): v for k, v in d.items()}
