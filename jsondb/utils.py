from typing import Any, Dict

def get_table_info(table_name: str, table_data: Any) -> Dict[str, Any]:
    """Returns a dictionary with detailed information about a table."""
    length = 0
    if isinstance(table_data, (list, dict, str)):
        length = len(table_data)
    
    return {
        "name": table_name,
        "type": type(table_data).__name__,
        "length": length,
        "data": table_data
    }

def format_for_display(data: Dict[str, Any]) -> str:
    """Formats the entire database or a single table for readable printing."""
    output = []
    if "name" in data and "type" in data: # It's a single table info
        output.append(f"=== Table: {data['name']} ===")
        output.append(f"Type: {data['type']}")
        output.append(f"Length: {data['length']}")
        output.append(f"Data: {data['data']}")
    else: # It's the entire database
        output.append("=== Entire Database ===")
        for key, value in data.items():
            info = get_table_info(key, value)
            output.append(f"Table: {info['name']}")
            output.append(f"  Type: {info['type']}")
            output.append(f"  Length: {info['length']}")
            output.append(f"  Data: {str(info['data'])[:100]}...") # Truncate for display
            output.append("-" * 20)
    return "\n".join(output)

