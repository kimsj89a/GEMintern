#!/usr/bin/env python3
"""
cli.py — DOCX Markup Tool CLI

다중 .docx 문서의 tracked changes를 비교, 병합하고
Clean / Redline 버전을 생성하는 명령줄 도구.

Usage:
    # 1) 단일 문서 markup 추출
    python cli.py extract doc.docx

    # 2) 다중 문서 비교
    python cli.py compare doc_v1.docx doc_v2.docx doc_v3.docx

    # 3) 다중 문서 변경사항 병합
    python cli.py merge doc_v1.docx doc_v2.docx -o merged/

    # 4) Clean + Redline 버전 생성
    python cli.py output doc.docx -o output/

    # 5) 풀 파이프라인 (비교 → 병합 → Clean/Redline)
    python cli.py pipeline doc_v1.docx doc_v2.docx -o result/ --use-claude

환경변수:
    ANTHROPIC_API_KEY  Claude API 키 (--use-claude 사용 시 필요)
"""

import argparse
import json
import os
import sys

from core import DocxParser, extract_all_changes, summarize_changes
from compare import ChangeComparer, format_comparison_report
from merge import ChangeMerger, ConflictStrategy, format_merge_report
from output import create_clean_version, create_redline_version, create_both_versions


def cmd_extract(args):
    """단일 문서 markup 추출"""
    for filepath in args.files:
        print(f"\n{'='*60}")
        print(f"파일: {os.path.basename(filepath)}")
        print(f"{'='*60}")

        parser = DocxParser(filepath)
        info = parser.get_info()
        changes = parser.extract_changes()

        print(f"총 문단: {info.paragraphs_total}")
        print(f"변경 수: {info.change_count}")
        print(f"수정자: {', '.join(info.authors)}")

        stats = summarize_changes(changes)
        print(f"\n유형별: {json.dumps(stats['by_type'], ensure_ascii=False, indent=2)}")

        # 의미있는 변경만 출력
        meaningful = [c for c in changes if c.text.strip() and not c.text.strip().isdigit()]
        print(f"\n--- 주요 변경사항 ({len(meaningful)}건) ---")
        for i, c in enumerate(meaningful, 1):
            type_kr = {
                "insertion": "추가", "deletion": "삭제",
                "format_change": "서식", "paragraph_mark_insertion": "문단추가",
                "paragraph_mark_deletion": "문단삭제",
            }.get(c.change_type, c.change_type)
            text = c.text.replace("\n", " ")[:100]
            print(f"  [{i:3d}] [{type_kr}] {c.author} | {text}")

        # JSON 출력 옵션
        if args.json:
            out_path = args.json if isinstance(args.json, str) else filepath + ".changes.json"
            data = [c.to_dict() for c in changes]
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\nJSON 저장: {out_path}")


def cmd_compare(args):
    """다중 문서 비교"""
    if len(args.files) < 2:
        print("비교하려면 2개 이상의 파일이 필요합니다.")
        sys.exit(1)

    file_changes = {}
    for fp in args.files:
        fname = os.path.basename(fp)
        parser = DocxParser(fp)
        file_changes[fname] = parser.extract_changes()

    comparer = ChangeComparer(similarity_threshold=args.threshold)
    result = comparer.compare_multiple(file_changes)
    report = format_comparison_report(result)
    print(report)

    if args.output:
        os.makedirs(args.output, exist_ok=True)
        report_path = os.path.join(args.output, "comparison_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n리포트 저장: {report_path}")


def cmd_merge(args):
    """다중 문서 변경사항 병합"""
    if len(args.files) < 2:
        print("병합하려면 2개 이상의 파일이 필요합니다.")
        sys.exit(1)

    # 충돌 전략 결정
    if args.use_claude:
        strategy = ConflictStrategy.ASK_CLAUDE
    elif args.strategy:
        strategy = ConflictStrategy(args.strategy)
    else:
        strategy = ConflictStrategy.KEEP_BOTH

    file_changes = {}
    for fp in args.files:
        fname = os.path.basename(fp)
        parser = DocxParser(fp)
        file_changes[fname] = parser.extract_changes()

    merger = ChangeMerger(
        conflict_strategy=strategy,
        claude_api_key=args.api_key or os.environ.get("ANTHROPIC_API_KEY"),
    )
    result = merger.merge_multiple(file_changes)
    report = format_merge_report(result)
    print(report)

    if args.output:
        os.makedirs(args.output, exist_ok=True)
        report_path = os.path.join(args.output, "merge_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n리포트 저장: {report_path}")

        # 병합 결과 JSON
        merged_path = os.path.join(args.output, "merged_changes.json")
        data = {
            "accepted": [c.to_dict() for c in result.accepted_changes],
            "rejected": [c.to_dict() for c in result.rejected_changes],
            "warnings": result.warnings,
        }
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"병합 결과 JSON: {merged_path}")


def cmd_output(args):
    """Clean + Redline 버전 생성"""
    output_dir = args.output or "."
    os.makedirs(output_dir, exist_ok=True)

    for filepath in args.files:
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        clean_path, redline_path = create_both_versions(filepath, output_dir, base_name)
        print(f"  Clean:   {clean_path}")
        print(f"  Redline: {redline_path}")


def cmd_pipeline(args):
    """풀 파이프라인: 비교 → 병합 → Clean/Redline"""
    output_dir = args.output or "pipeline_output"
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("STEP 1: 문서 로딩 및 변경사항 추출")
    print("=" * 60)

    file_changes = {}
    parsers = {}
    for fp in args.files:
        fname = os.path.basename(fp)
        parser = DocxParser(fp)
        parsers[fname] = (parser, fp)
        changes = parser.extract_changes()
        file_changes[fname] = changes
        stats = summarize_changes(changes)
        print(f"  {fname}: {stats['total']}건 ({', '.join(f'{k}:{v}' for k, v in stats['by_type'].items())})")

    if len(args.files) >= 2:
        print(f"\n{'='*60}")
        print("STEP 2: 다중 문서 비교")
        print("=" * 60)

        comparer = ChangeComparer(similarity_threshold=args.threshold)
        comparison = comparer.compare_multiple(file_changes)
        comp_report = format_comparison_report(comparison)
        print(comp_report)

        with open(os.path.join(output_dir, "01_comparison_report.txt"), "w", encoding="utf-8") as f:
            f.write(comp_report)

        print(f"\n{'='*60}")
        print("STEP 3: 변경사항 병합")
        print("=" * 60)

        strategy = ConflictStrategy.ASK_CLAUDE if args.use_claude else ConflictStrategy.KEEP_BOTH
        merger = ChangeMerger(
            conflict_strategy=strategy,
            claude_api_key=args.api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )
        merge_result = merger.merge_multiple(file_changes)
        merge_report = format_merge_report(merge_result)
        print(merge_report)

        with open(os.path.join(output_dir, "02_merge_report.txt"), "w", encoding="utf-8") as f:
            f.write(merge_report)

    print(f"\n{'='*60}")
    print("STEP 4: Clean / Redline 버전 생성")
    print("=" * 60)

    # 첫 번째 파일을 base로 사용
    base_file = args.files[0]
    base_name = os.path.splitext(os.path.basename(base_file))[0]

    clean_path = os.path.join(output_dir, f"{base_name}_CLEAN.docx")
    redline_path = os.path.join(output_dir, f"{base_name}_REDLINE.docx")

    create_clean_version(base_file, clean_path)
    create_redline_version(base_file, redline_path)

    print(f"  Clean:   {clean_path}")
    print(f"  Redline: {redline_path}")

    print(f"\n{'='*60}")
    print(f"완료! 결과물: {output_dir}/")
    print("=" * 60)


# ─── Main ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="DOCX Markup Tool — 다중 문서 tracked changes 비교/병합/출력",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", help="명령")

    # extract
    p_ext = subparsers.add_parser("extract", help="단일 문서 markup 추출")
    p_ext.add_argument("files", nargs="+", help=".docx 파일 경로")
    p_ext.add_argument("--json", nargs="?", const=True, help="JSON으로 내보내기")

    # compare
    p_cmp = subparsers.add_parser("compare", help="다중 문서 비교")
    p_cmp.add_argument("files", nargs="+", help=".docx 파일 경로 (2개 이상)")
    p_cmp.add_argument("-o", "--output", help="리포트 출력 디렉토리")
    p_cmp.add_argument("--threshold", type=float, default=0.7, help="유사도 임계값 (0~1, 기본 0.7)")

    # merge
    p_mrg = subparsers.add_parser("merge", help="다중 문서 변경사항 병합")
    p_mrg.add_argument("files", nargs="+", help=".docx 파일 경로 (2개 이상)")
    p_mrg.add_argument("-o", "--output", help="출력 디렉토리")
    p_mrg.add_argument("--strategy", choices=["keep_a", "keep_b", "keep_both", "ask_claude"],
                       help="충돌 해소 전략")
    p_mrg.add_argument("--use-claude", action="store_true", help="Claude API로 충돌 해소")
    p_mrg.add_argument("--api-key", help="Anthropic API 키")

    # output
    p_out = subparsers.add_parser("output", help="Clean/Redline 버전 생성")
    p_out.add_argument("files", nargs="+", help=".docx 파일 경로")
    p_out.add_argument("-o", "--output", help="출력 디렉토리")

    # pipeline
    p_pipe = subparsers.add_parser("pipeline", help="풀 파이프라인 (비교→병합→출력)")
    p_pipe.add_argument("files", nargs="+", help=".docx 파일 경로")
    p_pipe.add_argument("-o", "--output", default="pipeline_output", help="출력 디렉토리")
    p_pipe.add_argument("--use-claude", action="store_true", help="Claude API로 충돌 해소")
    p_pipe.add_argument("--api-key", help="Anthropic API 키")
    p_pipe.add_argument("--threshold", type=float, default=0.7, help="유사도 임계값")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "extract": cmd_extract,
        "compare": cmd_compare,
        "merge": cmd_merge,
        "output": cmd_output,
        "pipeline": cmd_pipeline,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
