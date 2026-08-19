import { describe, expect, it } from "vitest";

import { LOCAL_TRANSLATION_OPTIONS } from "./localTranslation";

describe("local translation model configuration", () => {
  it("uses browser-compatible 4-bit ONNX weights", () => {
    expect(LOCAL_TRANSLATION_OPTIONS).toMatchObject({
      device: "wasm",
      dtype: "q4",
    });
  });
});
