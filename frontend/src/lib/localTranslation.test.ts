import { describe, expect, it } from "vitest";

import { LOCAL_TRANSLATION_OPTIONS, LOCAL_TRANSLATION_TOKENIZER } from "./localTranslation";

describe("local translation model configuration", () => {
  it("uses browser-compatible 4-bit ONNX weights", () => {
    expect(LOCAL_TRANSLATION_OPTIONS).toMatchObject({
      device: "wasm",
      dtype: "q4",
    });
  });

  it("uses the matching fast tokenizer from the conversion package", () => {
    expect(LOCAL_TRANSLATION_TOKENIZER).toBe("R4kSo1997/opus-mt-en-ko-onnx-int8");
  });
});
