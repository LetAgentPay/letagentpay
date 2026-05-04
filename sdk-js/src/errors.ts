/** Error returned by the LetAgentPay API. */
export class LetAgentPayError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`[${status}] ${detail}`);
    this.name = "LetAgentPayError";
    this.status = status;
    this.detail = detail;
  }
}
