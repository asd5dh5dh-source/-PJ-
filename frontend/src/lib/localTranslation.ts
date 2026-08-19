type TranslationOutput = { translation_text?: string };

type TranslationPipeline = (
  text: string,
) => Promise<TranslationOutput | TranslationOutput[]>;

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
    translatorPromise = import("@huggingface/transformers").then(async ({ pipeline }) => {
      const createPipeline = pipeline as unknown as (
        task: string,
        model: string,
        options: Record<string, string>,
      ) => Promise<TranslationPipeline>;
      return createPipeline(
        "translation",
        "R4kSo1997/opus-mt-en-ko-onnx-int8",
        { device: "wasm" },
      );
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
