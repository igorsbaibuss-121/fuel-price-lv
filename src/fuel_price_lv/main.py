from pathlib import Path
import sys

import pandas as pd

from .cli import parse_args
from .importers.circlek_lv_v1 import CIRCLEK_CACHE_PATH, load_circlek_lv_v1_data, save_circlek_cache_csv
from .importers import load_input_data
from .reporting import build_report_summary, render_output_text, write_report_bundle
from .services import (
    annotate_price_conflicts,
    build_default_output_filename,
    build_history_snapshot_filename,
    build_history_source_label,
    build_result_title,
    deduplicate_results,
    filter_by_city,
    filter_by_fuel_type,
    filter_by_station_name,
    prepare_results,
    save_history_snapshot,
    summarize_cheapest_by_city,
)
from .source_catalog import get_multiple_source_configs, get_source_config


def cli_flag_was_provided(flag_name: str) -> bool:
    return flag_name in sys.argv[1:]


def configure_stdout_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def input_format_uses_local_file(input_format: str) -> bool:
    return input_format not in {"remote_csv_v1", "circlek_lv_v1", "neste_lv_v1", "virsi_lv_v1"}


def resolve_catalog_csv_path(csv_path_value: str, source_catalog_path: Path) -> str:
    csv_path = Path(csv_path_value)
    if csv_path.is_absolute() or csv_path.exists():
        return str(csv_path)

    same_dir_path = source_catalog_path.parent / csv_path
    if same_dir_path.exists():
        return str(same_dir_path)

    repo_root_path = source_catalog_path.parent.parent / csv_path
    if repo_root_path.exists():
        return str(repo_root_path)

    csv_path = same_dir_path
    return str(csv_path)


def apply_source_catalog_defaults(args) -> None:
    if not args.source_id:
        return

    source_catalog_path = Path(args.source_catalog)
    source_config = get_source_config(args.source_id, source_catalog_path)
    if not cli_flag_was_provided("--input-format") and "input_format" in source_config:
        args.input_format = source_config["input_format"]
    if not cli_flag_was_provided("--csv-path") and "csv_path" in source_config:
        args.csv_path = resolve_catalog_csv_path(source_config["csv_path"], source_catalog_path)
    if not cli_flag_was_provided("--source-url") and "source_url" in source_config:
        args.source_url = source_config["source_url"]


def parse_source_ids(value: str | None) -> list[str]:
    if value is None:
        return []

    source_ids = [source_id.strip() for source_id in value.split(",") if source_id.strip()]
    if not source_ids:
        raise ValueError("source-ids jānorāda vismaz viens source ID")
    return source_ids


def validate_source_selection(args) -> None:
    if args.source_id and args.source_ids:
        raise ValueError("Nevar vienlaikus lietot --source-id un --source-ids")
    if args.refresh_circlek and args.source_id != "circlek_live":
        raise ValueError("--refresh-circlek prasa --source-id circlek_live")


def load_single_input_source(
    csv_path: Path,
    input_format: str,
    source_url: str | None = None,
    ca_bundle: str | None = None,
) -> pd.DataFrame:
    if input_format_uses_local_file(input_format) and not csv_path.exists():
        raise ValueError(f"CSV fails nav atrasts: {csv_path}")
    return load_input_data(csv_path=csv_path, input_format=input_format, source_url=source_url, ca_bundle=ca_bundle)


def load_dataframe_for_source_config(
    source_id: str,
    source_config: dict,
    source_catalog_path: Path,
    ca_bundle: str | None = None,
) -> pd.DataFrame:
    input_format = source_config.get("input_format", "standard")
    csv_path_value = source_config.get("csv_path", "data/sample_prices.csv")
    if "csv_path" in source_config:
        csv_path_value = resolve_catalog_csv_path(csv_path_value, source_catalog_path)
    csv_path = Path(csv_path_value)
    source_url = source_config.get("source_url")

    df = load_single_input_source(
        csv_path=csv_path,
        input_format=input_format,
        source_url=source_url,
        ca_bundle=ca_bundle,
    )
    result_df = df.copy()
    result_df["source_id"] = source_id
    return result_df


def load_aggregated_source_data(
    source_ids: list[str],
    source_catalog_path: Path,
    ca_bundle: str | None = None,
) -> pd.DataFrame:
    source_configs = get_multiple_source_configs(source_ids, source_catalog_path)
    dataframes = [
        load_dataframe_for_source_config(source_id, source_config, source_catalog_path, ca_bundle=ca_bundle)
        for source_id, source_config in zip(source_ids, source_configs, strict=True)
    ]
    return pd.concat(dataframes, ignore_index=True)


def load_resolved_input_data(args) -> pd.DataFrame:
    source_ids = parse_source_ids(args.source_ids)
    if source_ids:
        args.source_ids = ",".join(source_ids)
        if args.ca_bundle is None:
            return load_aggregated_source_data(source_ids, Path(args.source_catalog))
        return load_aggregated_source_data(source_ids, Path(args.source_catalog), ca_bundle=args.ca_bundle)

    apply_source_catalog_defaults(args)
    return load_single_input_source(
        csv_path=Path(args.csv_path),
        input_format=args.input_format,
        source_url=args.source_url,
        ca_bundle=args.ca_bundle,
    )


def refresh_circlek_cache(args) -> Path:
    apply_source_catalog_defaults(args)
    dataset = load_circlek_lv_v1_data(ca_bundle=args.ca_bundle)
    return save_circlek_cache_csv(dataset, CIRCLEK_CACHE_PATH)


def build_history_snapshot_path(args) -> Path:
    source_label = build_history_source_label(
        source_id=args.source_id,
        source_ids=args.source_ids,
        input_format=args.input_format,
    )
    return Path("output") / "history" / build_history_snapshot_filename(
        fuel_type=args.fuel_type,
        source_label=source_label,
    )


def main() -> None:
    configure_stdout_encoding()
    args = parse_args()

    try:
        validate_source_selection(args)
        if args.refresh_circlek:
            cache_path = refresh_circlek_cache(args)
            print(f"Circle K cache saved: {cache_path}")
            return
        df = load_resolved_input_data(args)
    except ValueError as error:
        print(error)
        return

    if args.detect_price_conflicts:
        df = annotate_price_conflicts(df)

    if args.dedup:
        df = deduplicate_results(df)

    df = filter_by_fuel_type(df, args.fuel_type)
    if args.city:
        df = filter_by_city(df, args.city)
    if args.station:
        df = filter_by_station_name(df, args.station)

    if df.empty:
        print("Nav atrasti dati izvēlētajiem filtriem")
        return

    if args.report:
        top_n_result, saved_paths, provenance_stats = write_report_bundle(args, df)
        history_snapshot_path = None
        if args.save_history:
            history_snapshot_path = build_history_snapshot_path(args)
            save_history_snapshot(top_n_result, history_snapshot_path)
        print(build_report_summary(args, len(top_n_result), saved_paths, provenance_stats, history_snapshot_path))
        return

    if args.summary_by_city:
        result = summarize_cheapest_by_city(df)
    else:
        result = prepare_results(df, args.top_n, args.sort_by)

    if args.save_history:
        save_history_snapshot(result, build_history_snapshot_path(args))

    title = build_result_title(
        fuel_type=args.fuel_type,
        top_n=args.top_n,
        city=args.city,
        station_query=args.station,
        summary_by_city=args.summary_by_city,
    )

    output_text = render_output_text(result, args.output)

    output_path = None
    if args.output_file:
        output_path = Path(args.output_file)
    elif args.save:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / build_default_output_filename(
            fuel_type=args.fuel_type,
            output_format=args.output,
            top_n=args.top_n,
            city=args.city,
            station_query=args.station,
            summary_by_city=args.summary_by_city,
        )

    if output_path is not None:
        output_path.write_text(output_text, encoding="utf-8")
        print(f"Rezultāts saglabāts failā: {output_path}")
        return

    if args.output == "table":
        print(title)
        print()
    print(output_text)


if __name__ == "__main__":
    main()
