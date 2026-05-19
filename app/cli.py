from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from app.domain.models import Finding
from app.agents.readiness_agent import ReadinessAgent
from app.reports import markdown_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Go-Live Security Readiness Agent — SQA SA"
    )
    parser.add_argument("findings_file", help="Ruta al archivo JSON con findings")
    parser.add_argument("--product", required=True, help="Nombre del producto")
    parser.add_argument("--engagement", required=True, help="Nombre del engagement")
    parser.add_argument(
        "--go-live-date",
        required=True,
        help="Fecha objetivo de Go-Live (YYYY-MM-DD)",
    )
    parser.add_argument("--output", default=None, help="Archivo de salida .md (opcional)")
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Formato de salida",
    )

    args = parser.parse_args()

    findings_path = Path(args.findings_file)
    if not findings_path.exists():
        print(f"Error: no se encontró el archivo {findings_path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw_findings = json.loads(findings_path.read_text(encoding="utf-8"))
        findings = [Finding(**f) for f in raw_findings]
    except Exception as e:
        print(f"Error al leer findings: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        go_live_date = datetime.strptime(args.go_live_date, "%Y-%m-%d").date()
    except ValueError:
        print("Error: formato de fecha inválido. Use YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    agent = ReadinessAgent()
    report = agent.generate_report(
        product_name=args.product,
        engagement_name=args.engagement,
        target_go_live_date=go_live_date,
        findings=findings,
    )

    if args.format == "json":
        output_text = report.model_dump_json(indent=2)
    else:
        output_text = markdown_report.generate(report)

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"\nReporte guardado en: {args.output}")
    else:
        print(output_text)

    _print_summary(report)


def _print_summary(report) -> None:
    print("\n" + "=" * 60)
    print(f"RESULTADO: {report.overall_recommendation}")
    print("=" * 60)
    print(f"Bloqueantes:          {len(report.blockers)}")
    print(f"Alta prioridad:       {len(report.high_pre_go_live)}")
    print(f"Post Go-Live:         {len(report.post_go_live)}")
    print(f"Riesgo aceptado:      {len(report.accepted_risks)}")
    print(f"Evidencia faltante:   {len(report.missing_evidence)}")
    if report.blockers:
        print("\nBLOQUEANTES:")
        for b in report.blockers:
            print(f"  [{b.finding_id}] {b.title}")
    if report.missing_evidence:
        print("\nEVIDENCIA FALTANTE:")
        for m in report.missing_evidence:
            print(f"  - {m}")
    print("=" * 60)


if __name__ == "__main__":
    main()
