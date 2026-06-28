import { LitElement, html, css, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import "./amazing-irrigation-overview-card";
import {
  buildZoneView,
  canRun,
  canStop,
  type HassState,
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

@customElement("amazing-irrigation-card")
export class AmazingIrrigationCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: ZoneCardConfig;

  public static getStubConfig(): Partial<ZoneCardConfig> {
    return { decision_entity: "" };
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

  private _callZoneService(service: "run_zone" | "stop_zone", force = false) {
    if (!this.hass || !this._config) {
      return;
    }
    const data: Record<string, unknown> = {
      entity_id: this._config.decision_entity,
    };
    if (service === "run_zone") {
      data.force = force;
    }
    this.hass.callService("amazing_irrigation", service, data);
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
          ${this._metric("Target", this._pct(view.target))}
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
        ${this._renderHistory(view)}

        <div class="actions">
          <mwc-button
            raised
            ?disabled=${!canRun(view)}
            @click=${() => this._callZoneService("run_zone")}
            >Run</mwc-button
          >
          <mwc-button
            ?disabled=${!canRun(view)}
            @click=${() => this._callZoneService("run_zone", true)}
            >Force Water</mwc-button
          >
          ${canStop(view)
            ? html`<mwc-button
                class="stop"
                @click=${() => this._callZoneService("stop_zone")}
                >Stop</mwc-button
              >`
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
    }
    .stop {
      --mdc-theme-primary: var(--error-color);
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
