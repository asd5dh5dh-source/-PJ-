import type { ArchiveQuery, ArchiveSort } from "@/lib/types";

const textFields = [
  ["customer_name", "고객사"],
  ["product_equipment", "제품 / 설비"],
  ["voc_type", "VOC 유형"],
  ["voc_subtype", "VOC 세부 유형"],
  ["final_status", "최종 상태"],
  ["responsible_department", "담당 부서"],
] as const;

function readQuery(form: HTMLFormElement): ArchiveQuery {
  const data = new FormData(form);
  const query: ArchiveQuery = {};
  for (const [key, raw] of data.entries()) {
    const value = String(raw).trim();
    if (value) Object.assign(query, { [key]: value });
  }
  return query;
}

export default function ArchiveFilters({
  query,
  onApply,
}: {
  query: ArchiveQuery;
  onApply: (query: ArchiveQuery) => void;
}) {
  const effectiveSort: ArchiveSort = query.sort ?? (query.q ? "relevance" : "latest");

  return (
    <form
      className="filter-panel"
      key={new URLSearchParams(query as Record<string, string>).toString()}
      onSubmit={(event) => {
        event.preventDefault();
        const next = readQuery(event.currentTarget);
        if (next.q && !query.q) next.sort = "relevance";
        if (!next.q && next.sort === "relevance") next.sort = "latest";
        onApply(next);
      }}
    >
      <div className="search-row">
        <label className="search-field">
          <span>통합 검색</span>
          <input
            type="search"
            name="q"
            defaultValue={query.q ?? ""}
            placeholder="사례 ID, 요청 내용, 키워드 검색"
          />
        </label>
        <button className="primary-button" type="submit">검색</button>
      </div>

      <details className="advanced-filters" open={Object.keys(query).some((key) => !["q", "sort", "page"].includes(key))}>
        <summary>상세 필터</summary>
        <div className="filter-grid">
          {textFields.map(([name, label]) => (
            <label key={name}>
              <span>{label}</span>
              <input name={name} defaultValue={query[name] ?? ""} />
            </label>
          ))}
          <label>
            <span>접수 시작일</span>
            <input type="date" name="received_from" defaultValue={query.received_from ?? ""} />
          </label>
          <label>
            <span>접수 종료일</span>
            <input type="date" name="received_to" defaultValue={query.received_to ?? ""} />
          </label>
        </div>
      </details>

      <div className="filter-actions">
        <label className="sort-control">
          <span>정렬</span>
          <select
            name="sort"
            value={effectiveSort}
            onChange={(event) => onApply(readQuery(event.currentTarget.form!))}
          >
            {query.q && <option value="relevance">관련도순</option>}
            <option value="latest">최신순</option>
            <option value="oldest">오래된순</option>
          </select>
        </label>
        <button className="text-button" type="button" onClick={() => onApply({})}>필터 초기화</button>
      </div>
    </form>
  );
}
