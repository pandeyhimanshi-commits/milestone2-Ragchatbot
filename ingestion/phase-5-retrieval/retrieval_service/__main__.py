from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid

from retrieval_service.config import QUERY_TOP_K
from retrieval_service.runner import run_retrieval, seed_thread


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Phase 5 retrieval runtime (docs/rag-architecture.md §5).",
    )
    parser.add_argument("--query", type=str, help="User question for retrieval")
    parser.add_argument(
        "--thread-id",
        type=str,
        default=str(uuid.uuid4()),
        help="Opaque thread id used for bounded thread context",
    )
    parser.add_argument("--top-k", type=int, default=QUERY_TOP_K, help="Chroma candidate count")
    parser.add_argument(
        "--seed-scheme-slug",
        type=str,
        default="",
        help="Optional: seed thread context with a known scheme slug",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON response instead of compact summary",
    )
    args = parser.parse_args()

    if args.seed_scheme_slug:
        state = seed_thread(thread_id=args.thread_id, scheme_slug=args.seed_scheme_slug)
        print(
            json.dumps(
                {
                    "thread_id": state.thread_id,
                    "scheme_slug": state.scheme_slug,
                    "updated_at": state.updated_at,
                },
                indent=2,
            )
        )
        return

    if not args.query:
        parser.error("--query is required unless --seed-scheme-slug is used")

    resp = run_retrieval(query=args.query, thread_id=args.thread_id, top_k=args.top_k)
    if args.json:
        print(json.dumps(resp.to_json(), indent=2))
        return

    print(f"thread_id: {resp.thread_id}")
    print(f"decision: {resp.decision}")
    print(f"best_distance: {resp.confidence_best_distance}")
    print(f"scheme_slug: {resp.scheme_slug}")
    print(f"citation_url: {resp.citation_url}")
    if resp.message:
        print(f"message: {resp.message}")
    print("grounding:")
    for i, g in enumerate(resp.grounded[:3], start=1):
        print(f"{i}. {g.metadata.get('source_url')} (distance={g.distance})")
    sys.exit(0)


if __name__ == "__main__":
    main()

