import argparse


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("top-n jābūt pozitīvam veselam skaitlim")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fuel Price LV sample viewer")
    parser.add_argument("--fuel-type", required=True, help="Degvielas tips, piem. diesel vai petrol_95")
    parser.add_argument("--city", help="Pilsēta, piem. Rīga")
    parser.add_argument("--station", help="DUS nosaukuma daļa, piem. Neste")
    parser.add_argument("--source-id", help="Avota identifikators no source catalog faila")
    parser.add_argument("--source-ids", help="Ar komatiem atdalits source_id saraksts no source catalog faila")
    parser.add_argument("--source-catalog", default="data/source_catalog.json", help="Source catalog JSON faila ceļš")
    parser.add_argument("--csv-path", default="data/sample_prices.csv", help="CSV faila ceļš")
    parser.add_argument("--source-url", help="Attālināta CSV avota URL remote source formātiem")
    parser.add_argument("--ca-bundle", help="Papildu CA bundle fails SSL verifikācijai attālinātiem avotiem")
    parser.add_argument(
        "--input-format",
        choices=["standard", "raw_v1", "excel_v1", "remote_csv_v1", "circlek_lv_v1", "neste_lv_v1", "virsi_lv_v1", "viada_lv_v1"],
        default="standard",
    )
    parser.add_argument("--top-n", type=positive_int, default=5, help="Cik ierakstus rādīt")
    parser.add_argument("--sort-by", choices=["price_asc", "price_desc"], default="price_asc")
    parser.add_argument("--output", choices=["table", "csv", "json"], default="table")
    parser.add_argument("--output-file")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--summary-by-city", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--save-history", action="store_true")
    parser.add_argument("--dedup", action="store_true")
    parser.add_argument("--detect-price-conflicts", action="store_true")
    parser.add_argument("--refresh-circlek", action="store_true")
    return parser.parse_args()
