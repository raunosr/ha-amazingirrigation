import { LitElement, html, css, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import "./amazing-irrigation-overview-card";
import "./editor";
import {
  buildZoneView,
  canRun,
  canStop,
  decisionEntities,
  type ControlEntity,
  type HassState,
  type LearnedValue,
  type ModelInsight,
  type ModelParameter,
  type RelatedEntity,
  type ScheduleSlot,
  type WaterBalanceTerm,
  type ZoneCardConfig,
  type ZoneView,
} from "./zone-view";

interface HomeAssistant {
  states: Record<string, HassState>;
  callService: (
    domain: string,
    service: string,
    data?: Record<string, unknown>,
  ) => Promise<unknown>;
}

const KIND_LABELS: Record<string, string> = {
  run_request: "Run requested",
  decision: "Decision",
  rain_event: "Rain",
  watering_event: "Watering",
};

/** Turn a raw select option key (e.g. "good_garden") into a display label. */
function prettyOption(value: string | null): string {
  if (!value) {
    return "–";
  }
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/**
 * Single-zone detail card. Kept for backward compatibility — users who prefer
 * one card per zone can still use this. The overview card is now the primary
 * surface with built-in drill-down.
 */
@customElement("amazing-irrigation-card")
export class AmazingIrrigationCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: ZoneCardConfig;
  @state() private _actionPending: string | null = null;
  @state() private _actionResult: { kind: "ok" | "error"; text: string } | null =
    null;

  private _actionResultTimer?: ReturnType<typeof setTimeout>;

  public static getStubConfig(hass?: {
    states?: Record<string, HassState>;
  }): Partial<ZoneCardConfig> {
    const [decision] = decisionEntities(hass?.states);
    return { decision_entity: decision ?? "" };
  }

  public static async getConfigElement(): Promise<HTMLElement> {
    return document.createElement("amazing-irrigation-card-editor");
  }

  public setConfig(config: ZoneCardConfig): void {
    if (!config || !config.decision_entity) {
      throw new Error("amazing-irrigation-card: 'decision_entity' is required");
    }
    this._config = config;
  }

  public getCardSize(): number {
    return 4;
  }

  private get _view(): ZoneView | undefined {
    if (!this._config || !this.hass) {
      return undefined;
    }
    return buildZoneView(this._config, this.hass.states);
  }

  private async _callZoneService(
    service: "run_zone" | "stop_zone",
    force = false,
  ) {
    if (!this.hass || !this._config || this._actionPending) {
      return;
    }
    const actionKey =
      service === "stop_zone" ? "stop" : force ? "force" : "run";
    this._actionPending = actionKey;
    this._actionResult = null;
    if (this._actionResultTimer) clearTimeout(this._actionResultTimer);

    const data: Record<string, unknown> = {
      entity_id: this._config.decision_entity,
    };
    if (service === "run_zone") {
      data.force = force;
    }

    try {
      await this.hass.callService("amazing_irrigation", service, data);
      const label =
        actionKey === "stop"
          ? "Stop sent"
          : force
            ? "Force sent"
            : "Run sent";
      this._actionResult = { kind: "ok", text: label };
    } catch {
      this._actionResult = { kind: "error", text: "Service call failed" };
    } finally {
      this._actionPending = null;
      this._actionResultTimer = setTimeout(() => {
        this._actionResult = null;
      }, 4000);
    }
  }

  public disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._actionResultTimer) clearTimeout(this._actionResultTimer);
  }

  /** Open Home Assistant's more-info dialog so the user can edit a value. */
  private _moreInfo(entityId: string) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  /** Toggle a switch entity (schedule active, zone enabled, learning). */
  private _toggleSwitch(entityId: string) {
    if (!this.hass) {
      return;
    }
    this.hass.callService("switch", "toggle", { entity_id: entityId });
  }

  protected render(): TemplateResult | typeof nothing {
    const view = this._view;
    if (!this._config) {
      return nothing;
    }
    if (!view) {
      return html`<ha-card><div class="empty">Loading…</div></ha-card>`;
    }

    return html`
      <ha-card>
        <div class="header">
          <span class="name">${view.name}</span>
          <span class="status ${view.isWatering ? "active" : ""}">
            ${view.wateringStatus ?? "idle"}
          </span>
        </div>

        <div class="grid">
          ${this._metric("Moisture", this._pct(view.moisture))}
          ${view.targetMode === "auto" &&
          view.targetBandLow !== null &&
          view.targetBandHigh !== null
            ? this._metric(
                "Target band",
                `${Math.round(view.targetBandLow)}–${Math.round(
                  view.targetBandHigh,
                )}%`,
              )
            : this._metric("Target", this._pct(view.target))}
          ${view.demandProfile === null
            ? nothing
            : this._metric(
                "Demand",
                view.demandProfile.charAt(0).toUpperCase() +
                  view.demandProfile.slice(1),
              )}
          ${this._metric(
            "Recommended",
            view.recommendedLiters === null
              ? "–"
              : `${view.recommendedLiters} L`,
          )}
          ${view.availableWater === null
            ? nothing
            : this._metric(
                "Available water",
                `${Math.round(view.availableWater * 100)}%`,
              )}
          ${view.totalVolume === null
            ? nothing
            : this._metric(
                "Total water",
                `${view.totalVolume} ${view.totalVolumeUnit ?? "L"}`,
              )}
        </div>

        <div class="decision">
          <span class="decision-action">${view.decision ?? "–"}</span>
          ${view.decisionReason
            ? html`<span class="decision-reason"
                >${view.decisionReason.replace(/_/g, " ")}</span
              >`
            : nothing}
        </div>

        ${this._renderGreenhouse(view)}
        ${this._renderControls(view)}
        ${this._renderSchedule(view)}
        ${this._renderLearned(view)}
        ${this._renderModelInsight(view)}
        ${this._renderReferences(view)}
        ${this._renderHistory(view)}

        <div class="actions">
          <mwc-button
            raised
            ?disabled=${!canRun(view) || !!this._actionPending}
            @click=${() => this._callZoneService("run_zone")}
          >
            ${this._actionPending === "run"
              ? html`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`
              : nothing}
            Run
          </mwc-button>
          <mwc-button
            ?disabled=${!canRun(view) || !!this._actionPending}
            @click=${() => this._callZoneService("run_zone", true)}
          >
            ${this._actionPending === "force"
              ? html`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`
              : nothing}
            Force Water
          </mwc-button>
          ${canStop(view)
            ? html`<mwc-button
                class="stop"
                ?disabled=${!!this._actionPending}
                @click=${() => this._callZoneService("stop_zone")}
              >
                ${this._actionPending === "stop"
                  ? html`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`
                  : nothing}
                Stop
              </mwc-button>`
            : nothing}
          ${this._actionResult
            ? html`<span class="action-feedback ${this._actionResult.kind}">
                <ha-icon
                  icon=${this._actionResult.kind === "ok"
                    ? "mdi:check-circle-outline"
                    : "mdi:alert-circle-outline"}
                ></ha-icon>
                ${this._actionResult.text}
              </span>`
            : nothing}
        </div>
      </ha-card>
    `;
  }

  private _renderGreenhouse(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.greenhouse) {
      return nothing;
    }
    return html`
      <div class="greenhouse">
        <span class="badge">🌱 Greenhouse</span>
        <span class="ctx ${view.protectedRain ? "on" : ""}">
          ${view.protectedRain ? "Protected from rain" : "Open to rain"}
        </span>
        ${view.temperature !== null
          ? html`<span class="ctx">${view.temperature}°C</span>`
          : nothing}
        ${view.humidity !== null
          ? html`<span class="ctx">${view.humidity}% RH</span>`
          : nothing}
      </div>
    `;
  }

  private _renderControls(view: ZoneView): TemplateResult | typeof nothing {
    const isAuto =
      view.autoTargetControl?.isOn ?? view.targetMode === "auto";
    const numbers = [
      isAuto ? null : view.targetControl,
      view.maxLitersControl,
      view.sensorDepthControl,
      view.rainFractionControl,
      view.minApplicationControl,
    ].filter((c): c is ControlEntity => c !== null);
    const selects = [
      view.soilTypeControl,
      view.plantProfileControl,
    ].filter((c): c is ControlEntity => c !== null);
    const toggles = [
      view.enabledControl,
      view.learningControl,
      view.autoTargetControl,
    ].filter((c): c is ControlEntity => c !== null);
    const hasBand =
      isAuto && view.targetBandLow !== null && view.targetBandHigh !== null;
    if (!numbers.length && !toggles.length && !selects.length && !hasBand) {
      return nothing;
    }
    return html`
      <div class="section">
        <div class="section-head">Settings</div>
        ${hasBand
          ? html`
              <div class="row">
                <span class="row-label">Target band (auto)</span>
                <span class="row-value"
                  >${Math.round(view.targetBandLow!)}–${Math.round(
                    view.targetBandHigh!,
                  )} %</span
                >
              </div>
            `
          : nothing}
        ${selects.map(
          (c) => html`
            <div
              class="row clickable"
              @click=${() => this._moreInfo(c.entityId)}
            >
              <span class="row-label">${c.label}</span>
              <span class="row-value">${prettyOption(c.state)}</span>
            </div>
          `,
        )}
        ${numbers.map(
          (c) => html`
            <div
              class="row clickable"
              @click=${() => this._moreInfo(c.entityId)}
            >
              <span class="row-label">${c.label}</span>
              <span class="row-value"
                >${c.state ?? "–"} ${c.unit ?? ""}</span
              >
            </div>
          `,
        )}
        ${view.sensorDepthShallow
          ? html`
              <div class="row warning">
                <ha-icon icon="mdi:alert-outline"></ha-icon>
                <span class="row-label"
                  >Sensor sits well above the root zone — moisture may read low
                  and over-trigger watering.</span
                >
              </div>
            `
          : nothing}
        ${toggles.map(
          (c) => html`
            <div class="row">
              <span class="row-label">${c.label}</span>
              <button
                class="toggle ${c.isOn ? "on" : ""}"
                @click=${() => this._toggleSwitch(c.entityId)}
              >
                ${c.isOn ? "On" : "Off"}
              </button>
            </div>
          `,
        )}
      </div>
    `;
  }

  private _renderSchedule(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.schedule.length) {
      return nothing;
    }
    return html`
      <div class="section">
        <div class="section-head">Schedule</div>
        ${view.schedule.map(
          (slot: ScheduleSlot) => html`
            <div class="row">
              <span
                class="row-label clickable"
                @click=${() => this._moreInfo(slot.timeEntity)}
                >Schedule ${slot.index}</span
              >
              <span
                class="row-value clickable"
                @click=${() => this._moreInfo(slot.timeEntity)}
                >${slot.time ?? "–"}</span
              >
              <button
                class="toggle ${slot.active ? "on" : ""}"
                @click=${() => this._toggleSwitch(slot.activeEntity)}
              >
                ${slot.active ? "Active" : "Off"}
              </button>
            </div>
          `,
        )}
      </div>
    `;
  }

  private _renderLearned(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.learned.length) {
      return nothing;
    }
    return html`
      <div class="section">
        <div class="section-head">Learned model</div>
        ${view.learned.map(
          (item: LearnedValue) => html`
            <div
              class="row clickable"
              @click=${() => this._moreInfo(item.entityId)}
            >
              <span class="row-label">${item.label}</span>
              <span class="row-value">
                ${item.value === null
                  ? "learning…"
                  : `${item.value} ${item.unit ?? ""}`}
              </span>
            </div>
          `,
        )}
      </div>
    `;
  }

  private _renderReferences(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.references.length) {
      return nothing;
    }
    return html`
      <div class="section">
        <div class="section-head">Sensors</div>
        ${view.references.map(
          (ref: RelatedEntity) => html`
            <div
              class="row clickable"
              @click=${() => this._moreInfo(ref.entityId)}
            >
              <span class="row-label">${ref.label}</span>
              <span class="row-value"
                >${ref.state ?? "–"} ${ref.unit ?? ""}</span
              >
            </div>
          `,
        )}
      </div>
    `;
  }

  private _renderModelInsight(view: ZoneView): TemplateResult | typeof nothing {
    const insight = view.modelInsight;
    if (!insight) {
      return nothing;
    }
    const explanation = insight.decisionExplanation;
    return html`
      <details class="section model-insight">
        <summary>
          <span>Why this decision</span>
          ${insight.status ? html`<span>${insight.status}</span>` : nothing}
        </summary>
        ${insight.bootstrapSummary
          ? html`<div class="model-note">${insight.bootstrapSummary}</div>`
          : nothing}
        ${explanation ? this._renderDecisionExplanation(explanation) : nothing}
        ${insight.parameters.length
          ? html`
              <div class="section-head">Model parameters</div>
              ${insight.parameters.map((param) =>
                this._renderModelParameter(param),
              )}
            `
          : nothing}
        ${insight.modelUpdated
          ? html`<div class="model-note">
              Updated ${new Date(insight.modelUpdated).toLocaleString()}
            </div>`
          : nothing}
      </details>
    `;
  }

  private _renderDecisionExplanation(
    explanation: NonNullable<ModelInsight["decisionExplanation"]>,
  ): TemplateResult {
    return html`
      <div class="model-note">
        ${explanation.predictiveReason
          ? `Reason: ${explanation.predictiveReason.replace(/_/g, " ")}`
          : "Predictive water-balance decision"}
        ${explanation.horizonHours === null
          ? ""
          : ` over ${explanation.horizonHours} h`}
        ${explanation.chosenLiters === null
          ? ""
          : ` · chosen ${explanation.chosenLiters} L`}
      </div>
      ${explanation.predictedTrajectory.length
        ? html`
            <div class="section-head">Predicted moisture trajectory</div>
            <div class="trajectory">
              ${explanation.predictedTrajectory.map(
                (value, index) =>
                  html`<span>Step ${index + 1}: ${value}%</span>`,
              )}
            </div>
          `
        : nothing}
      ${explanation.predictedCriticalTheta !== null ||
      explanation.predictedPeakTheta !== null
        ? html`<div class="model-note">
            ${explanation.predictedCriticalTheta === null
              ? ""
              : `Lowest predicted moisture: ${explanation.predictedCriticalTheta}%`}
            ${explanation.predictedPeakTheta === null
              ? ""
              : ` Peak: ${explanation.predictedPeakTheta}%`}
          </div>`
        : nothing}
      ${explanation.terms.length
        ? html`
            <div class="section-head">Water-balance terms</div>
            ${explanation.terms.map((term) => this._renderTerm(term))}
          `
        : nothing}
    `;
  }

  private _renderTerm(term: WaterBalanceTerm): TemplateResult {
    const sign = term.value > 0 ? "+" : "";
    return html`
      <div class="row">
        <span class="row-label">${term.label}</span>
        <span class="row-value">${sign}${term.value} ${term.unit}</span>
      </div>
    `;
  }

  private _renderModelParameter(param: ModelParameter): TemplateResult {
    return html`
      <div class="row model-param">
        <span class="row-label">${param.label}</span>
        <span class="row-value">
          ${param.value === null ? "learning…" : `${param.value} ${param.unit ?? ""}`}
          ${param.confidence === null
            ? nothing
            : html`<span class="confidence">
                <span
                  style="width: ${Math.round(param.confidence * 100)}%"
                ></span>
              </span>
              ${Math.round(param.confidence * 100)}%`}
        </span>
      </div>
    `;
  }

  private _renderHistory(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.historyEntries.length) {
      return nothing;
    }
    const recent = view.historyEntries.slice(0, 5);
    return html`
      <div class="history">
        <div class="history-head">
          History (${view.historyCount})
        </div>
        <ul>
          ${recent.map((entry) => {
            const kind = String(entry["kind"] ?? "");
            return html`<li>
              <span class="kind">${KIND_LABELS[kind] ?? kind}</span>
              <span class="detail">${this._historyDetail(entry)}</span>
            </li>`;
          })}
        </ul>
      </div>
    `;
  }

  private _historyDetail(entry: Record<string, unknown>): string {
    if (entry["action"]) {
      return `${entry["action"]} (${entry["reason"] ?? ""})`;
    }
    if (entry["status"]) {
      const liters = entry["measured_liters"] ?? entry["requested_liters"];
      return liters === null || liters === undefined
        ? String(entry["status"])
        : `${entry["status"]} · ${liters} L`;
    }
    if (entry["delta_mm"] !== undefined) {
      return `+${entry["delta_mm"]} mm`;
    }
    return "";
  }

  private _metric(label: string, value: string): TemplateResult {
    return html`<div class="metric">
      <div class="metric-value">${value}</div>
      <div class="metric-label">${label}</div>
    </div>`;
  }

  private _pct(value: number | null): string {
    return value === null ? "–" : `${value}%`;
  }

  public static styles = css`
    ha-card {
      padding: 16px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .name {
      font-size: 1.2rem;
      font-weight: 600;
    }
    .status {
      text-transform: capitalize;
      font-size: 0.85rem;
      color: var(--secondary-text-color);
    }
    .status.active {
      color: var(--primary-color);
      font-weight: 600;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
      gap: 8px;
      margin-bottom: 12px;
    }
    .metric {
      text-align: center;
      padding: 8px 4px;
      background: var(--secondary-background-color);
      border-radius: 8px;
    }
    .metric-value {
      font-size: 1.1rem;
      font-weight: 600;
    }
    .metric-label {
      font-size: 0.75rem;
      color: var(--secondary-text-color);
    }
    .decision {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 12px;
    }
    .decision-action {
      text-transform: capitalize;
      font-weight: 600;
    }
    .decision-reason {
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
    .greenhouse {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
      margin-bottom: 12px;
    }
    .greenhouse .badge {
      font-weight: 600;
      font-size: 0.85rem;
    }
    .greenhouse .ctx {
      font-size: 0.8rem;
      padding: 2px 6px;
      border-radius: 6px;
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
    }
    .greenhouse .ctx.on {
      color: var(--primary-color);
    }
    .section {
      margin-bottom: 12px;
    }
    .section-head {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--secondary-text-color);
      margin-bottom: 4px;
    }
    details.model-insight {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 8px;
    }
    details.model-insight summary {
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--secondary-text-color);
    }
    .model-note {
      color: var(--secondary-text-color);
      font-size: 0.8rem;
      margin: 6px 0;
    }
    .trajectory {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin: 4px 0 8px;
    }
    .trajectory span {
      background: var(--secondary-background-color);
      border-radius: 10px;
      font-size: 0.75rem;
      padding: 2px 6px;
    }
    .confidence {
      display: inline-block;
      width: 40px;
      height: 6px;
      background: var(--divider-color);
      border-radius: 6px;
      margin-left: 6px;
      overflow: hidden;
      vertical-align: middle;
    }
    .confidence span {
      display: block;
      height: 100%;
      background: var(--primary-color);
    }
    .row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.85rem;
      padding: 4px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .row-label {
      flex: 1;
    }
    .row-value {
      color: var(--secondary-text-color);
      text-align: right;
    }
    .row.warning {
      color: var(--warning-color, #ff9800);
      font-size: 0.78rem;
      align-items: flex-start;
    }
    .row.warning ha-icon {
      --mdc-icon-size: 18px;
      flex: 0 0 auto;
    }
    .clickable {
      cursor: pointer;
    }
    .clickable:hover {
      color: var(--primary-color);
    }
    .toggle {
      border: 1px solid var(--divider-color);
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
      border-radius: 12px;
      padding: 2px 10px;
      font-size: 0.75rem;
      cursor: pointer;
    }
    .toggle.on {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      border-color: var(--primary-color);
    }
    .history {
      margin-bottom: 12px;
    }
    .history-head {
      font-size: 0.85rem;
      color: var(--secondary-text-color);
      margin-bottom: 4px;
    }
    .history ul {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .history li {
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      padding: 2px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .history .detail {
      color: var(--secondary-text-color);
    }
    .actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    .actions mwc-button[disabled] {
      opacity: 0.5;
      pointer-events: none;
    }
    .actions ha-circular-progress {
      --mdc-theme-primary: currentColor;
      margin-inline-end: 4px;
    }
    .stop {
      --mdc-theme-primary: var(--error-color);
    }
    .action-feedback {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.82rem;
      font-weight: 500;
      padding: 2px 8px;
      border-radius: 12px;
      animation: feedback-in 200ms ease-out;
    }
    .action-feedback.ok {
      color: var(--success-color, #4caf50);
    }
    .action-feedback.error {
      color: var(--error-color, #f44336);
    }
    .action-feedback ha-icon {
      --mdc-icon-size: 16px;
    }
    @keyframes feedback-in {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @media (prefers-reduced-motion: reduce) {
      .action-feedback { animation: none; }
    }
    .empty {
      padding: 16px;
      color: var(--secondary-text-color);
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "amazing-irrigation-card": AmazingIrrigationCard;
  }
  interface Window {
    customCards?: Array<Record<string, unknown>>;
  }
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "amazing-irrigation-card",
  name: "Amazing Irrigation Zone",
  description: "Display and control a single Amazing Irrigation zone.",
});
