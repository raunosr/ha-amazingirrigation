import { LitElement, html, css, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import {
  buildOverview,
  decisionEntities,
  type HassState,
  type OverviewCardConfig,
  type ZoneView,
} from "./zone-view";

interface HomeAssistant {
  states: Record<string, HassState>;
}

@customElement("amazing-irrigation-overview-card")
export class AmazingIrrigationOverviewCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: OverviewCardConfig;

  public static getStubConfig(hass?: {
    states?: Record<string, HassState>;
  }): Partial<OverviewCardConfig> {
    const zones = decisionEntities(hass?.states).map((entity) => ({
      decision_entity: entity,
    }));
    return { zones };
  }

  public static async getConfigElement(): Promise<HTMLElement> {
    return document.createElement("amazing-irrigation-overview-card-editor");
  }

  public setConfig(config: OverviewCardConfig): void {
    if (!config || !Array.isArray(config.zones) || config.zones.length === 0) {
      throw new Error(
        "amazing-irrigation-overview-card: 'zones' must list at least one zone",
      );
    }
    for (const zone of config.zones) {
      if (!zone.decision_entity) {
        throw new Error(
          "amazing-irrigation-overview-card: each zone needs 'decision_entity'",
        );
      }
    }
    this._config = config;
  }

  public getCardSize(): number {
    return this._config ? this._config.zones.length + 1 : 1;
  }

  protected render(): TemplateResult | typeof nothing {
    if (!this._config || !this.hass) {
      return nothing;
    }
    const views = buildOverview(this._config, this.hass.states);
    return html`
      <ha-card>
        ${this._config.title
          ? html`<div class="title">${this._config.title}</div>`
          : nothing}
        <div class="zones">
          ${views.map((view) => this._renderRow(view))}
        </div>
      </ha-card>
    `;
  }

  private _renderRow(view: ZoneView): TemplateResult {
    return html`
      <div class="zone">
        <div class="primary">
          <span class="name">
            ${view.greenhouse ? html`<span class="gh">🌱</span>` : nothing}
            ${view.name}
          </span>
          <span class="decision">${view.decision ?? "–"}</span>
        </div>
        <div class="secondary">
          <span
            >${view.moisture === null ? "–" : `${view.moisture}%`}
            ${view.target === null ? "" : `/ ${view.target}%`}</span
          >
          <span class="status ${view.isWatering ? "active" : ""}">
            ${view.wateringStatus ?? "idle"}
          </span>
          ${view.greenhouse && view.protectedRain
            ? html`<span class="ctx">rain-protected</span>`
            : nothing}
          ${view.greenhouse && view.temperature !== null
            ? html`<span class="ctx">${view.temperature}°C</span>`
            : nothing}
          ${view.greenhouse && view.humidity !== null
            ? html`<span class="ctx">${view.humidity}% RH</span>`
            : nothing}
        </div>
      </div>
    `;
  }

  public static styles = css`
    ha-card {
      padding: 16px;
    }
    .title {
      font-size: 1.2rem;
      font-weight: 600;
      margin-bottom: 8px;
    }
    .zone {
      padding: 8px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .zone:last-child {
      border-bottom: none;
    }
    .primary {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .name {
      font-weight: 600;
    }
    .gh {
      margin-right: 4px;
    }
    .decision {
      text-transform: capitalize;
      color: var(--primary-color);
      font-size: 0.9rem;
    }
    .secondary {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 2px;
      font-size: 0.8rem;
      color: var(--secondary-text-color);
    }
    .status.active {
      color: var(--primary-color);
      font-weight: 600;
    }
    .ctx {
      padding: 1px 6px;
      border-radius: 6px;
      background: var(--secondary-background-color);
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "amazing-irrigation-overview-card": AmazingIrrigationOverviewCard;
  }
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "amazing-irrigation-overview-card",
  name: "Amazing Irrigation Overview",
  description: "Compact multi-zone overview for Amazing Irrigation.",
});
