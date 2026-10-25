"""第1回: LLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask -t 1.5 -n 3 "LoRAとは何ですか？"   # 基礎: temperature を変えて3回
    uv run python -m app.ask --chat      # 実装: 会話履歴を保って続けて質問する
    uv run python -m app.ask --bench     # 発展: モデル・質問ごとに時間とトークン数を計測する

通常はツールも会話履歴も持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse
import time
from dataclasses import dataclass

from google import genai
from google.genai import errors, types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"

# --bench で比べる既定の質問（一般的な用語 / 講座に固有のこと）
BENCH_QUESTIONS = ["LoRAとは何ですか？", DEFAULT_QUESTION]


@dataclass
class Result:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    seconds: float


def _tokens(response) -> tuple[int | None, int | None]:
    usage = response.usage_metadata
    if usage is None:
        return None, None
    return usage.prompt_token_count, usage.candidates_token_count


def _config(temperature: float | None) -> types.GenerateContentConfig | None:
    if temperature is None:
        return None
    return types.GenerateContentConfig(temperature=temperature)


def ask(
    question: str,
    model: str = MODEL,
    temperature: float | None = None,
    client: genai.Client | None = None,
) -> Result:
    client = client or genai.Client(api_key=get_api_key())
    start = time.perf_counter()
    response = client.models.generate_content(
        model=model, contents=question, config=_config(temperature)
    )
    seconds = time.perf_counter() - start
    input_tokens, output_tokens = _tokens(response)
    return Result(response.text, input_tokens, output_tokens, seconds)


def format_usage(result: Result) -> str:
    return (
        f"[tokens] 入力={result.input_tokens} 出力={result.output_tokens} "
        f"/ {result.seconds:.2f}秒"
    )


def chat_loop(
    model: str = MODEL,
    temperature: float | None = None,
    client: genai.Client | None = None,
) -> None:
    """会話履歴を保ったまま、空行か Ctrl-D で終わるまで質問を続ける。"""
    client = client or genai.Client(api_key=get_api_key())
    chat = client.chats.create(model=model, config=_config(temperature))
    print("会話モード（終了: 空行 / exit / Ctrl-D）")
    while True:
        try:
            question = input("\n> ").strip()
        except EOFError:
            break
        if question in ("", "exit", "quit"):
            break
        start = time.perf_counter()
        response = chat.send_message(question)
        seconds = time.perf_counter() - start
        print(response.text)
        input_tokens, output_tokens = _tokens(response)
        # 履歴ぶん、ターンが進むほど入力トークンが増えることが見える
        print(format_usage(Result(response.text, input_tokens, output_tokens, seconds)))


def bench(models: list[str], questions: list[str], repeat: int = 3) -> list[dict]:
    """モデル×質問ごとに repeat 回呼び、平均の応答時間とトークン数を表にする。"""
    client = genai.Client(api_key=get_api_key())
    rows = []
    for model in models:
        for question in questions:
            results, errors_seen = [], []
            for _ in range(repeat):
                try:
                    results.append(ask(question, model=model, client=client))
                except errors.APIError as e:
                    errors_seen.append(e.code)
            row = {"model": model, "question": question, "ok": len(results),
                   "errors": errors_seen}
            if results:
                row["seconds"] = sum(r.seconds for r in results) / len(results)
                row["input"] = sum(r.input_tokens or 0 for r in results) / len(results)
                row["output"] = sum(r.output_tokens or 0 for r in results) / len(results)
            rows.append(row)
    print("| model | 質問 | 成功/試行 | 平均秒 | 平均入力tok | 平均出力tok | エラー |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(
            f"| {r['model']} | {r['question'][:16]} | {r['ok']}/{repeat} | "
            f"{r.get('seconds', float('nan')):.2f} | {r.get('input', float('nan')):.0f} | "
            f"{r.get('output', float('nan')):.0f} | {r['errors'] or '-'} |"
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="LLMに質問する")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("-m", "--model", default=MODEL)
    parser.add_argument("-t", "--temperature", type=float, default=None)
    parser.add_argument("-n", "--repeat", type=int, default=1, help="同じ質問を繰り返す回数")
    parser.add_argument("--chat", action="store_true", help="会話履歴を保って続けて質問する")
    parser.add_argument("--bench", nargs="*", metavar="MODEL",
                        help="モデル名を並べて応答時間とトークン数を比較する（省略時は --model のみ）")
    args = parser.parse_args()

    try:
        if args.bench is not None:
            bench(args.bench or [args.model], BENCH_QUESTIONS, args.repeat if args.repeat > 1 else 3)
        elif args.chat:
            print(f"[model] {args.model}")
            chat_loop(args.model, args.temperature)
        else:
            print(f"[model] {args.model} [temperature] {args.temperature}")
            print(f"[質問] {args.question}")
            for i in range(args.repeat):
                print(f"\n--- {i + 1}/{args.repeat} ---")
                result = ask(args.question, args.model, args.temperature)
                print(result.text)
                print(format_usage(result))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
