from pathlib import Path
import sys

from .cli import parse_args
from .importers import load_input_data
from .reporting import build_report_summary, render_output_text, write_report_bundle
from .services import (
    build_default_output_filename,
    build_result_title,
    filter_by_city,
    filter_by_fuel_type,
    filter_by_station_name,
    prepare_results,
    summarize_cheapest_by_city,
)
from .source_catalog import get_source_config


def cli_flag_was_provided(flag_name: str) -> bool:
    return flag_name in sys.argv[1:]


def configure_stdout_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def apply_source_catalog_defaults(args) -> None:
    if not args.source_id:
        return

    source_catalog_path = Path(args.source_catalog)
    source_config = get_source_config(args.source_id, source_catalog_path)
    if not cli_flag_was_provided("--input-format") and "input_format" in source_config:
        args.input_format = source_config["input_format"]
    if not cli_flag_was_provided("--csv-path") and "csv_path" in source_config:
        csv_path = Path(source_config["csv_path"])
        if not csv_path.is_absolute() and not csv_path.exists():
            csv_path = source_catalog_path.parent / csv_path
        args.csv_path = str(csv_path)
    if not cli_flag_was_provided("--source-url") and "source_url" in source_config:
        args.source_url = source_config["source_url"]


def main() -> None:
    configure_stdout_encoding()
    args = parse_args()

    try:
        apply_source_catalog_defaults(args)
    except ValueError as error:
        print(error)
        return

    csv_path = Path(args.csv_path)
    if args.input_format != "remote_csv_v1" and not csv_path.exists():
        print(f"CSV fails nav atrasts: {csv_path}")
        return

    try:
        df = load_input_data(csv_path=csv_path, input_format=args.input_format, source_url=args.source_url)
    except ValueError as error:
        print(error)
        return

    df = filter_by_fuel_type(df, args.fuel_type)
    if args.city:
        df = filter_by_city(df, args.city)
    if args.station:
        df = filter_by_station_name(df, args.station)

    if df.empty:
        print("Nav atrasti dati izv\u0113l\u0113tajiem filtriem")
        return

    if args.report:
        top_n_result, saved_paths = write_report_bundle(args, df)
        print(build_report_summary(args, len(top_n_result), saved_paths))
        return

    if args.summary_by_city:
        result = summarize_cheapest_by_city(df)
    else:
        result = prepare_results(df, args.top_n, args.sort_by)

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
        print(f"Rezult\u0101ts saglab\u0101ts fail\u0101: {output_path}")
        return

    if args.output == "table":
        print(title)
        print()
    print(output_text)


if __name__ == "__main__":
    main()
