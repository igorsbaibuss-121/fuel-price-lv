from pathlib import Path

import pandas as pd

from .services import (
    add_google_maps_url_column,
    build_default_output_filename,
    prepare_results,
    summarize_cheapest_by_city,
)


def serialize_output_dataframe(result: pd.DataFrame, output_format: str) -> pd.DataFrame:
    serialized_df = add_google_maps_url_column(result)
    if output_format == "csv" and "source_ids" in serialized_df.columns:
        serialized_df = serialized_df.copy()
        serialized_df["source_ids"] = serialized_df["source_ids"].map(
            lambda value: "|".join(value) if isinstance(value, list) else value
        )
    if output_format == "csv" and "price_values" in serialized_df.columns:
        serialized_df = serialized_df.copy()
        serialized_df["price_values"] = serialized_df["price_values"].map(
            lambda value: "|".join(f"{item:.3f}" for item in value) if isinstance(value, list) else value
        )
    return serialized_df


def render_output_text(result: pd.DataFrame, output_format: str) -> str:
    serialized_df = serialize_output_dataframe(result, output_format)
    if output_format == "csv":
        return serialized_df.to_csv(index=False)
    if output_format == "json":
        return serialized_df.to_json(orient="records", force_ascii=False, indent=2)
    return result.to_string(index=False)


def build_report_source_label(args) -> str:
    if args.source_id:
        return args.source_id
    if args.source_ids:
        return args.source_ids
    if args.source_url:
        return args.source_url
    if args.input_format == "circlek_lv_v1":
        return "circlek_lv_v1"
    if args.input_format == "neste_lv_v1":
        return "neste_lv_v1"
    return str(args.csv_path)


def build_report_provenance_stats(df: pd.DataFrame) -> dict[str, float]:
    if "source_count" not in df.columns:
        return {}
    return {
        "deduplicated_count": len(df),
        "multi_source_confirmed_count": int((df["source_count"] > 1).sum()),
    }


def build_report_conflict_stats(df: pd.DataFrame) -> dict[str, float]:
    if "has_price_conflict" not in df.columns:
        return {}
    return {
        "conflict_count": int(df["has_price_conflict"].sum()),
        "max_price_range": float(df["price_range"].max()),
    }


def write_report_bundle(args, df: pd.DataFrame, output_dir: Path | None = None) -> tuple[pd.DataFrame, list[Path], dict[str, float]]:
    report_output_dir = output_dir or Path("output")
    report_output_dir.mkdir(exist_ok=True)

    top_n_result = prepare_results(df, args.top_n, args.sort_by)
    summary_by_city_result = summarize_cheapest_by_city(df)

    summary_stats: dict[str, float] = {}
    if args.dedup:
        summary_stats.update(build_report_provenance_stats(top_n_result))
    if args.detect_price_conflicts:
        summary_stats.update(build_report_conflict_stats(top_n_result))

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

    return top_n_result, [top_n_csv_path, top_n_json_path, summary_csv_path], summary_stats


def build_report_summary(args, result_count: int, saved_paths: list[Path], summary_stats: dict[str, float] | None = None) -> str:
    summary_lines = [
        f"Avots: {build_report_source_label(args)}",
        f"Fuel type: {args.fuel_type}",
        f"Atrasti ieraksti: {result_count}",
    ]
    if summary_stats:
        if "deduplicated_count" in summary_stats:
            summary_lines.append(f"Deduplicēti ieraksti: {summary_stats['deduplicated_count']}")
        if "multi_source_confirmed_count" in summary_stats:
            summary_lines.append(f"Ar vairākiem avotiem apstiprināti: {summary_stats['multi_source_confirmed_count']}")
        if "conflict_count" in summary_stats:
            summary_lines.append(f"Cenu konflikti: {summary_stats['conflict_count']}")
        if "max_price_range" in summary_stats:
            summary_lines.append(f"Maksimālā cenu starpība: {summary_stats['max_price_range']:.3f}")
    summary_lines.append("Saglabāti faili:")
    summary_lines.extend(f"- {path.as_posix()}" for path in saved_paths)
    return "\n".join(summary_lines)
