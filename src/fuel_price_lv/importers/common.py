def normalize_text_value(value: object, lowercase: bool = False) -> str:
    normalized_value = " ".join(str(value).split())
    if lowercase:
        normalized_value = normalized_value.lower()
    return normalized_value


def normalize_price_value(value: object, source_column: str) -> float:
    normalized_value = str(value).strip().replace(",", ".")
    try:
        return float(normalized_value)
    except ValueError as error:
        raise ValueError(f"Nederīga {source_column} vērtība ievades failā: {value}") from error
