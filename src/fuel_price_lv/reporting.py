from pathlib import Path

import pandas as pd

from .services import (
    add_google_maps_url_column,
    build_default_output_filename,
    prepare_results,
    summarize_cheapest_by_city,
)


def render_output_text(result: pd.DataFrame, output_format: str) -> str:
    if output_format == "csv":
        return add_google_maps_url_column(result).to_csv(index=False)
    if output_format == "json":
        return add_google_maps_url_column(result).to_json(orient="records", force_ascii=False, indent=2)
    return result.to_string(index=False)


def build_report_source_label(args) -> str:
    if args.source_id:
        return args.source_id
    if args.source_url:
        return args.source_url
    return str(args.csv_path)


def write_report_bundle(args, df: pd.DataFrame, output_dir: Path | None = None) -> tuple[pd.DataFrame, list[Path]]:
    report_output_dir = output_dir or Path("output")
    report_output_dir.mkdir(exist_ok=True)

    top_n_result = prepare_results(df, args.top_n, args.sort_by)
    summary_by_city_result = summarize_cheapest_by_city(df)

    top_n_csv_path = report_output_dir / build_default_output_filename(
        fuel_type=args.fuel_type,
        output_format="csv",
        top_n=args.top_n,
        city=args.city,
        station_query=args.station,
    )
    top_n_json_path = report_output_dir / build_default_output_filename(
        fuel_type=args.fuel_type,
        output_format="json",
        top_n=args.top_n,
        city=args.city,
        station_query=args.station,
    )
    summary_csv_path = report_output_dir / build_default_output_filename(
        fuel_type=args.fuel_type,
        output_format="csv",
        top_n=args.top_n,
        city=args.city,
        station_query=args.station,
        summary_by_city=True,
    )

    top_n_csv_path.write_text(render_output_text(top_n_result, "csv"), encoding="utf-8")
    top_n_json_path.write_text(render_output_text(top_n_result, "json"), encoding="utf-8")
    summary_csv_path.write_text(render_output_text(summary_by_city_result, "csv"), encoding="utf-8")

    return top_n_result, [top_n_csv_path, top_n_json_path, summary_csv_path]


def build_report_summary(args, result_count: int, saved_paths: list[Path]) -> str:
    summary_lines = [
        f"Avots: {build_report_source_label(args)}",
        f"Fuel type: {args.fuel_type}",
        f"Atrasti ieraksti: {result_count}",
        "Saglab\u0101ti faili:",
    ]
    summary_lines.extend(f"- {path.as_posix()}" for path in saved_paths)
    return "\n".join(summary_lines)
