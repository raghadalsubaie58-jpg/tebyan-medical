"""
train_lora.py — LoRA fine-tuning for Arabic medical report analysis.

Supports:
  - core42/jais-13b-chat (Arabic-English bilingual)
  - meta-llama/Llama-3.2-1B-Instruct (lightweight)
  - meta-llama/Llama-3.1-8B-Instruct (production quality)
  - inceptionai/jais-adapted-7b-chat

Requirements:
    pip install transformers peft datasets accelerate bitsandbytes trl

Usage:
    python training/train_lora.py \
        --model_name core42/jais-13b-chat \
        --data_dir data/ \
        --output_dir checkpoints/jais-medical-v1 \
        --num_epochs 3 \
        --batch_size 2 \
        --lora_r 16 \
        --lora_alpha 32 \
        --load_4bit

Hardware: Minimum 16GB VRAM (A100/H100 recommended for Jais-13B).
For smaller GPUs: use --load_4bit --gradient_checkpointing
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model_name",   default="meta-llama/Llama-3.2-1B-Instruct")
    p.add_argument("--data_dir",     default="data")
    p.add_argument("--output_dir",   default="checkpoints/tebyan-medical-v1")
    p.add_argument("--num_epochs",   type=int,   default=3)
    p.add_argument("--batch_size",   type=int,   default=2)
    p.add_argument("--grad_accum",   type=int,   default=4)
    p.add_argument("--lr",           type=float, default=2e-4)
    p.add_argument("--max_seq_len",  type=int,   default=2048)
    p.add_argument("--lora_r",       type=int,   default=16)
    p.add_argument("--lora_alpha",   type=int,   default=32)
    p.add_argument("--lora_dropout", type=float, default=0.05)
    p.add_argument("--lora_target",  nargs="+",  default=["q_proj", "v_proj", "k_proj", "o_proj"])
    p.add_argument("--load_4bit",    action="store_true")
    p.add_argument("--load_8bit",    action="store_true")
    p.add_argument("--gradient_checkpointing", action="store_true")
    p.add_argument("--warmup_ratio", type=float, default=0.05)
    p.add_argument("--save_steps",   type=int,   default=100)
    p.add_argument("--eval_steps",   type=int,   default=100)
    p.add_argument("--hf_token",     default=os.getenv("HF_TOKEN", ""))
    return p.parse_args()


def load_dataset(data_dir: str):
    from datasets import Dataset
    import pandas as pd

    def load_jsonl(path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    train = load_jsonl(Path(data_dir) / "train.jsonl")
    val   = load_jsonl(Path(data_dir) / "val.jsonl")

    if not train:
        raise FileNotFoundError(
            f"No train.jsonl found in {data_dir}. Run prepare_dataset.py first."
        )

    print(f"[train] loaded {len(train)} train, {len(val)} val examples")
    return Dataset.from_list(train), Dataset.from_list(val)


def format_prompt(example: dict) -> str:
    """Convert Alpaca-format example to model-specific chat template."""
    system  = example.get("system", "")
    instr   = example.get("instruction", "")
    inp     = example.get("input", "")
    output  = example.get("output", "")
    full_input = f"{instr}\n{inp}".strip() if inp else instr
    return (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system}"
        f"<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{full_input}"
        f"<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n{output}<|eot_id|>"
    )


def main():
    args = parse_args()

    # ── Imports (deferred so script is importable without GPU) ──────────────
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForCausalLM,
        TrainingArguments, BitsAndBytesConfig,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer

    print(f"[train] model={args.model_name} device={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'}")

    # ── Quantization config ───────────────────────────────────────────────
    bnb_config = None
    if args.load_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    elif args.load_8bit:
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)

    # ── Load tokenizer + model ────────────────────────────────────────────
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name, token=args.hf_token or None, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        token=args.hf_token or None,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if not bnb_config else None,
    )

    if bnb_config:
        model = prepare_model_for_kbit_training(model)

    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    # ── LoRA config ───────────────────────────────────────────────────────
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=args.lora_target,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── Dataset ────────────────────────────────────────────────────────────
    train_ds, val_ds = load_dataset(args.data_dir)

    # ── Training arguments ────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        save_strategy="steps",
        save_steps=args.save_steps,
        evaluation_strategy="steps",
        eval_steps=args.eval_steps,
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        fp16=not args.load_4bit,
        bf16=False,
        report_to="none",
        dataloader_num_workers=0,
        group_by_length=True,
    )

    # ── Trainer ────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds if val_ds else None,
        tokenizer=tokenizer,
        formatting_func=format_prompt,
        max_seq_length=args.max_seq_len,
        dataset_text_field=None,
    )

    print(f"[train] starting training | epochs={args.num_epochs}")
    trainer.train()

    # ── Save ───────────────────────────────────────────────────────────────
    out = Path(args.output_dir)
    model.save_pretrained(out / "lora_adapter")
    tokenizer.save_pretrained(out / "lora_adapter")
    print(f"[train] LoRA adapter saved → {out / 'lora_adapter'}")

    # Save training config
    (out / "training_config.json").write_text(
        json.dumps(vars(args), indent=2, ensure_ascii=False)
    )
    print("[train] Done.")


if __name__ == "__main__":
    main()
