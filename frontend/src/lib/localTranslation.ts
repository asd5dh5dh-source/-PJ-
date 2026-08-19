type TranslationOutput = { translation_text?: string };

type TranslationPipeline = (
  text: string,
) => Promise<TranslationOutput | TranslationOutput[]>;

const LOCAL_TRANSLATION_MODEL = "noticemkjung/opus-mt-tc-big-en-ko-ONNX";
export const LOCAL_TRANSLATION_TOKENIZER = "R4kSo1997/opus-mt-en-ko-onnx-int8";
export const LOCAL_TRANSLATION_OPTIONS = { device: "wasm", dtype: "q4" } as const;

let translatorPromise: Promise<TranslationPipeline> | undefined;

function splitForTranslation(text: string) {
  const chunks: string[] = [];
  let remaining = text.trim();
  while (remaining.length > 600) {
    const boundary = Math.max(
      remaining.lastIndexOf(". ", 600),
      remaining.lastIndexOf("\n", 600),
      remaining.lastIndexOf(" ", 600),
    );
    const end = boundary > 0 ? boundary + 1 : 600;
    chunks.push(remaining.slice(0, end));
    remaining = remaining.slice(end);
  }
  if (remaining) chunks.push(remaining);
  return chunks;
}

async function getTranslator(): Promise<TranslationPipeline> {
  if (!translatorPromise) {
    translatorPromise = import("@huggingface/transformers").then(async (transformers) => {
      const [tokenizer, model] = await Promise.all([
        transformers.AutoTokenizer.from_pretrained(LOCAL_TRANSLATION_TOKENIZER),
        transformers.AutoModelForSeq2SeqLM.from_pretrained(
          LOCAL_TRANSLATION_MODEL,
          LOCAL_TRANSLATION_OPTIONS,
        ),
      ]);
      return new transformers.TranslationPipeline({
        task: "translation",
        tokenizer,
        model,
      }) as TranslationPipeline;
    });
  }
  return translatorPromise;
}

export async function translateToKorean(text: string) {
  const translator = await getTranslator();
  const translated = [];
  for (const chunk of splitForTranslation(text)) {
    const output = await translator(chunk);
    const first = Array.isArray(output) ? output[0] : output;
    if (!first?.translation_text) throw new Error("번역 결과를 만들지 못했습니다.");
    translated.push(first.translation_text);
  }
  return translated.join("\n").trim();
}
