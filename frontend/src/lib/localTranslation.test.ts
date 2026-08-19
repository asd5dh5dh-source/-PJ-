import { describe, expect, it } from "vitest";

import { LOCAL_TRANSLATION_OPTIONS, LOCAL_TRANSLATION_TOKENIZER } from "./localTranslation";

describe("local translation model configuration", () => {
  it("uses the browser-compatible INT8 ONNX model directory", () => {
    expect(LOCAL_TRANSLATION_OPTIONS).toMatchObject({
      device: "wasm",
      dtype: "fp32",
      subfolder: "int8",
    });
  });

  it("uses the matching fast tokenizer from the conversion package", () => {
    expect(LOCAL_TRANSLATION_TOKENIZER).toBe("R4kSo1997/opus-mt-en-ko-onnx-int8");
  });
});
