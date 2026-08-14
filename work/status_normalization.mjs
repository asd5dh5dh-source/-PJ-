export function normalizeFinalStatus(status) {
  return status === "Closed" || status === "종결" ? "closed" : status;
}
