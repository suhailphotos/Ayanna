"""
LoRA / PEFT fine-tuning entry-point.

Run:

    poetry run python -m imgseg.train.train --config configs/lora.yaml
"""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("models/rmbg2.0/finetuned"))
    args = parser.parse_args()

    # TODO-next: load dataset, set up PEFT, train, save checkpoint
    print(f"Stub training loop — dataset @ {args.dataset}, ckpt → {args.output}")


if __name__ == "__main__":
    main()
