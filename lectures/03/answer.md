# 第3回 解答

## 演習

- 第1回（素のLLM）とエージェントの回答の違い：「lecNN-start タグ」を聞くと、第1回は講座の資料を見られないので「レッスンの開始を示す目印」と推測で答えていた。エージェントは用語集を引いて「各回の演習開始時点のコードに付けた Git タグ」と正しく答えた
- `--trace` で見えたツール呼び出し（ツール名と引数）：`search_glossary({'query': 'LoRA'})` と `search_glossary({'query': 'QLoRA'})` の2回。用語を1つずつ分けて検索していた
- 1つの質問での LLM 呼び出し回数（`requests`）：2回（ツールを呼ぶ判断で1回、結果を見て回答で1回）
- 追加したツールと、docstring に書いた説明：`make_quiz(lecture: int)`。「指定した回の用語から1つ選び、確認問題と答えを返す。問題やクイズを求められたときに使う」と書いた。「第2回の内容から確認問題を1問出して」で `make_quiz({'lecture': 2})` が呼ばれた

## 宿題

- 取り組んだレベル：基礎
- やったこと：`INSTRUCTIONS` から「用語や講座に固有のことを答える前に、必ず search_glossary で用語集を確認する。」の行を消して、同じ質問を `--trace` 付きで実行して比べた（比べたあとは元に戻した）
- 結果：
  - 「LoRAとQLoRAの違いは？」：消す前も消した後も `search_glossary` を LoRA と QLoRA で1回ずつ、計2回呼んだ。requests=2 も同じ
  - 「lecNN-start タグとは？」：消す前も後も `search_glossary({'query': 'lecNN-start タグ'})` を1回呼んだ。回答もほぼ同じ
  - 検索せずに答えるようにはならなかった
- 気づき・疑問：`search_glossary` の docstring にも「この講座に固有の言葉について答える前に使うこと」と書いてあるので、INSTRUCTIONS を消しても docstring だけで検索していたっぽい。docstring のほうも消したら検索しなくなるのかは試していない
