import type { VocRound, VocStage } from "@/lib/types";

export const stageLabels: Record<VocStage, string> = {
  received: "요청 접수",
  managing: "관리 중",
  in_progress: "대응 중",
  department_work: "부서별 검토 요청",
  department_review: "부서 직책자 검토",
  manager_review: "고정 최종 승인",
  final_review: "최종 검토",
  customer_reply: "고객 회신",
  completed: "완료",
  cancelled: "취소",
  deleted: "삭제",
};

function time(value?: string) {
  return value ? new Date(value).toLocaleString("ko-KR") : "—";
}

export default function VocTimeline({ rounds }: { rounds: VocRound[] }) {
  return (
    <section className="filter-panel" aria-labelledby="timeline-heading">
      <h2 id="timeline-heading">요청 라운드와 단계 이력</h2>
      <div className="timeline-list">
        {rounds.map((round) => (
          <article key={round.id}>
            <header><h3>{round.round_number}차 요청</h3><span className="status-badge">{stageLabels[round.stage]}</span></header>
            <p>{round.customer_request}</p>
            <h4>한국어 회신 초안</h4><p className="preserve-lines">{round.translation_final || round.translation_draft || "초안 없음"}</p>
            <details>
              <summary>원본 메일 보기</summary>
              <h4>원본 메일</h4><p className="preserve-lines">{round.original_mail_body || "내용 없음"}</p>
            </details>
            <ol>
              {round.stage_history.map((item) => (
                <li key={item.id}>
                  <strong>{item.from_stage ? stageLabels[item.from_stage] : "시작"} → {stageLabels[item.to_stage]}</strong>
                  <span>{item.changed_by} · {time(item.changed_at)}</span>
                  {item.reason && <p>{item.reason}</p>}
                  {item.ecm_link && <a href={item.ecm_link} target="_blank" rel="noreferrer">ECM 문서</a>}
                </li>
              ))}
            </ol>
          </article>
        ))}
      </div>
    </section>
  );
}
