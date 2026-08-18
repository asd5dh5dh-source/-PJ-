"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import { verifyWriter } from "@/lib/api";
import type { WriterCredentials } from "@/lib/types";

export type RequestWriter = (
  action: (writer: WriterCredentials) => void | Promise<void>,
) => void;

export default function WriterGate({
  children,
}: {
  children: (requestWriter: RequestWriter) => ReactNode;
}) {
  const [writer, setWriter] = useState<WriterCredentials>();
  const [open, setOpen] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(false);
  const pendingAction = useRef<((credentials: WriterCredentials) => void | Promise<void>) | null>(null);
  const dialog = useRef<HTMLElement>(null);
  const firstInput = useRef<HTMLInputElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  function restoreFocus() {
    queueMicrotask(() => returnFocus.current?.focus());
  }

  function closeDialog() {
    pendingAction.current = null;
    setError(false);
    setOpen(false);
    restoreFocus();
  }

  useEffect(() => {
    if (!open) return;
    firstInput.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDialog();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = [...(dialog.current?.querySelectorAll<HTMLElement>(
        "input, button:not(:disabled), select, textarea, [href], [tabindex]:not([tabindex='-1'])",
      ) ?? [])];
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const requestWriter: RequestWriter = (action) => {
    if (writer) {
      void Promise.resolve(action(writer));
      return;
    }
    returnFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    pendingAction.current = action;
    setError(false);
    setOpen(true);
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (verifying) return;
    const form = new FormData(event.currentTarget);
    const candidate = {
      writer_name: String(form.get("writer_name") ?? "").trim(),
      password: String(form.get("password") ?? ""),
    };
    if (!candidate.writer_name || !candidate.password) {
      setError(true);
      return;
    }
    setVerifying(true);
    setError(false);
    try {
      await verifyWriter(candidate);
      setWriter(candidate);
      setOpen(false);
      const action = pendingAction.current;
      pendingAction.current = null;
      restoreFocus();
      if (action) await action(candidate);
    } catch {
      setError(true);
    } finally {
      setVerifying(false);
    }
  }

  return (
    <>
      {writer && (
        <div className="writer-session" role="status">
          <span>{writer.writer_name} 작성자로 인증됨</span>
          <button
            className="text-button"
            type="button"
            onClick={() => setWriter(undefined)}
          >
            작성자 변경
          </button>
        </div>
      )}
      {children(requestWriter)}
      {open && (
        <div className="dialog-backdrop">
          <section ref={dialog} className="writer-dialog" role="dialog" aria-modal="true" aria-labelledby="writer-gate-title" aria-describedby="writer-gate-description">
            <h2 id="writer-gate-title">작성자 확인</h2>
            <p id="writer-gate-description">변경 이력에 남길 작성자명과 공용 비밀번호를 입력하세요.</p>
            <form onSubmit={(event) => void submit(event)}>
              <label><span>작성자명</span><input ref={firstInput} name="writer_name" autoFocus autoComplete="off" /></label>
              <label><span>공용 비밀번호</span><input name="password" type="password" autoComplete="off" /></label>
              {error && <p role="alert">인증하지 못했습니다. 입력값을 확인해 주세요.</p>}
              <div className="button-row">
                <button className="secondary-button" type="button" onClick={closeDialog}>취소</button>
                <button className="primary-button" type="submit" disabled={verifying}>
                  {verifying ? "인증 중..." : "인증 후 계속"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
