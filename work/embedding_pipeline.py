import argparse
import json
from pathlib import Path


DIMENSION = 384


def serialize_vector(vector):
    if len(vector) != DIMENSION:
        raise ValueError(f"Expected a {DIMENSION}-dimension vector, got {len(vector)}")
    return "[" + ",".join(f"{float(value):.8f}" for value in vector) + "]"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    from sentence_transformers import SentenceTransformer

    records = json.loads(Path(args.input).read_text(encoding="utf-8"))
    unique_texts = []
    seen = set()
    for record in records:
        for field in ("customer_request", "original_mail_body"):
            text = (record.get(field) or "").strip()
            if text and text not in seen:
                seen.add(text)
                unique_texts.append(text)

    model = SentenceTransformer(args.model, local_files_only=True)
    vectors = model.encode(
        unique_texts,
        batch_size=16,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    serialized_by_text = {
        text: serialize_vector(vector) for text, vector in zip(unique_texts, vectors)
    }

    output = {}
    for record in records:
        case_id = record["case_id"]
        request = (record.get("customer_request") or "").strip()
        mail = (record.get("original_mail_body") or "").strip()
        output[case_id] = {
            "customer_request_embedding": serialized_by_text.get(request),
            "original_mail_body_embedding": serialized_by_text.get(mail),
        }

    Path(args.output).write_text(
        json.dumps(output, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
