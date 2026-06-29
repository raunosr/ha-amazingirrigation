import { LitElement, html, css, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import {
  buildOverview,
  buildZoneView,
  canRun,
  canStop,
  decisionEntities,
  type ControlEntity,
  type HassState,
  type ModelParameter,
  type OverviewCardConfig,
  type RelatedEntity,
  type ScheduleSlot,
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

const DEFAULT_ZONE_ICON = "mdi:sprinkler-variant";

@customElement("amazing-irrigation-overview-card")
export class AmazingIrrigationOverviewCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: OverviewCardConfig;
  @state() private _activeZoneIndex: number | null = null;

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
    return this._config ? Math.ceil(this._config.zones.length / 2) + 2 : 3;
  }

  private _openZone(index: number): void {
    this._activeZoneIndex = index;
  }

  private _closeZone(): void {
    this._activeZoneIndex = null;
  }

  private _callZoneService(
    decisionEntity: string,
    service: "run_zone" | "stop_zone",
    force = false,
  ) {
    if (!this.hass) return;
    const data: Record<string, unknown> = { entity_id: decisionEntity };
    if (service === "run_zone") data.force = force;
    this.hass.callService("amazing_irrigation", service, data);
  }

  private _moreInfo(entityId: string) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _toggleSwitch(entityId: string) {
    if (!this.hass) return;
    this.hass.callService("switch", "toggle", { entity_id: entityId });
  }

  protected render(): TemplateResult | typeof nothing {
    if (!this._config || !this.hass) return nothing;

    if (this._activeZoneIndex !== null) {
      const zoneConfig = this._config.zones[this._activeZoneIndex];
      if (!zoneConfig) {
        this._activeZoneIndex = null;
        return nothing;
      }
      const view = buildZoneView(zoneConfig, this.hass.states);
      return this._renderDetail(view, zoneConfig);
    }

    return this._renderOverview();
  }

  /* ─── Overview Grid ─────────────────────────────────────────── */

  private _renderOverview(): TemplateResult {
    const views = buildOverview(this._config!, this.hass!.states);
    return html`
      <ha-card>
        ${this._config!.title
          ? html`<div class="card-header">${this._config!.title}</div>`
          : nothing}
        <div class="zone-grid">
          ${views.map((view, i) => this._renderZoneTile(view, i))}
        </div>
      </ha-card>
    `;
  }

  private _renderZoneTile(view: ZoneView, index: number): TemplateResult {
    const config = this._config!.zones[index];
    const icon = config.icon || DEFAULT_ZONE_ICON;
    const moisturePct =
      view.moisture !== null && view.target !== null && view.target > 0
        ? Math.min(100, Math.round((view.moisture / view.target) * 100))
        : view.moisture ?? 0;

    const statusClass = view.isWatering
      ? "watering"
      : view.decision === "skip"
        ? "skip"
        : view.decision === "water"
          ? "pending-water"
          : "";

    return html`
      <button
        class="zone-tile ${statusClass}"
        @click=${() => this._openZone(index)}
      >
        <div class="tile-icon-wrap">
          <ha-icon .icon=${icon}></ha-icon>
          ${view.isWatering
            ? html`<span class="tile-pulse"></span>`
            : nothing}
        </div>
        <span class="tile-name">${view.name}</span>
        <div class="tile-bar-track">
          <div
            class="tile-bar-fill"
            style="width: ${moisturePct}%"
          ></div>
          ${view.target !== null
            ? html`<div
                class="tile-bar-target"
                style="left: ${Math.min(100, view.target)}%"
              ></div>`
            : nothing}
        </div>
        <div class="tile-stats">
          <span class="tile-moisture"
            >${view.moisture !== null ? `${view.moisture}%` : "–"}</span
          >
          ${view.target !== null
            ? html`<span class="tile-target">/ ${view.target}%</span>`
            : nothing}
        </div>
      </button>
    `;
  }

  /* ─── Detail View ───────────────────────────────────────────── */

  private _renderDetail(
    view: ZoneView,
    config: ZoneCardConfig,
  ): TemplateResult {
    return html`
      <ha-card class="detail-card">
        <div class="detail-header">
          <button class="back-btn" @click=${this._closeZone}>
            <ha-icon icon="mdi:arrow-left"></ha-icon>
          </button>
          <ha-icon
            class="detail-icon"
            .icon=${config.icon || DEFAULT_ZONE_ICON}
          ></ha-icon>
          <div class="detail-title">
            <span class="detail-name">${view.name}</span>
            <span class="detail-status ${view.isWatering ? "active" : ""}">
              ${view.wateringStatus ?? "idle"}
            </span>
          </div>
        </div>

        ${this._renderMoistureSection(view)}
        ${this._renderDecisionBanner(view)}
        ${this._renderPrediction(view)}
        ${this._renderGreenhouse(view)}
        ${this._renderControls(view)}
        ${this._renderSchedule(view)}
        ${this._renderModelInsight(view)}
        ${this._renderReferences(view)}
        ${this._renderHistory(view)}

        <div class="detail-actions">
          <mwc-button
            raised
            ?disabled=${!canRun(view)}
            @click=${() =>
              this._callZoneService(config.decision_entity, "run_zone")}
          >
            <ha-icon icon="mdi:play" slot="icon"></ha-icon>
            Run
          </mwc-button>
          <mwc-button
            ?disabled=${!canRun(view)}
            @click=${() =>
              this._callZoneService(config.decision_entity, "run_zone", true)}
          >
            <ha-icon icon="mdi:water" slot="icon"></ha-icon>
            Force
          </mwc-button>
          ${canStop(view)
            ? html`<mwc-button
                class="stop-btn"
                @click=${() =>
                  this._callZoneService(config.decision_entity, "stop_zone")}
              >
                <ha-icon icon="mdi:stop" slot="icon"></ha-icon>
                Stop
              </mwc-button>`
            : nothing}
        </div>
      </ha-card>
    `;
  }

  private _renderMoistureSection(view: ZoneView): TemplateResult {
    const bandLow = view.targetBandLow ?? view.target ?? 0;
    const bandHigh = view.targetBandHigh ?? view.target ?? 100;
    const moisture = view.moisture ?? 0;
    const pct = Math.min(100, Math.max(0, moisture));

    return html`
      <div class="moisture-section">
        <div class="moisture-gauge">
          <div class="gauge-labels">
            <span class="gauge-current">${view.moisture ?? "–"}%</span>
            <span class="gauge-sublabel">Zone Moisture</span>
          </div>
          <div class="gauge-bar-wrap">
            <div class="gauge-bar-track">
              ${view.targetBandLow !== null && view.targetBandHigh !== null
                ? html`<div
                    class="gauge-target-band"
                    style="left: ${bandLow}%; width: ${bandHigh - bandLow}%"
                  ></div>`
                : view.target !== null
                  ? html`<div
                      class="gauge-target-line"
                      style="left: ${view.target}%"
                    ></div>`
                  : nothing}
              <div class="gauge-fill" style="width: ${pct}%"></div>
              <div class="gauge-marker" style="left: ${pct}%"></div>
            </div>
            <div class="gauge-ticks">
              <span>0%</span>
              ${view.targetBandLow !== null
                ? html`<span style="left:${bandLow}%">${Math.round(bandLow)}</span>`
                : nothing}
              ${view.targetBandHigh !== null
                ? html`<span style="left:${bandHigh}%">${Math.round(bandHigh)}</span>`
                : nothing}
              <span>100%</span>
            </div>
          </div>
        </div>

        <div class="metric-row">
          ${this._metric("Target", view.targetMode === "auto" && view.targetBandLow !== null && view.targetBandHigh !== null
            ? `${Math.round(view.targetBandLow)}–${Math.round(view.targetBandHigh)}%`
            : view.target !== null ? `${view.target}%` : "–")}
          ${view.recommendedLiters !== null
            ? this._metric("Recommended", `${view.recommendedLiters} L`)
            : nothing}
          ${view.availableWater !== null
            ? this._metric("Available", `${Math.round(view.availableWater * 100)}%`)
            : nothing}
          ${view.totalVolume !== null
            ? this._metric("Total Used", `${view.totalVolume} ${view.totalVolumeUnit ?? "L"}`)
            : nothing}
        </div>
      </div>
    `;
  }

  private _renderDecisionBanner(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.decision) return nothing;
    const cls =
      view.decision === "water"
        ? "water"
        : view.decision === "skip"
          ? "skip"
          : "neutral";
    return html`
      <div class="decision-banner ${cls}">
        <span class="decision-label">${view.decision}</span>
        ${view.decisionReason
          ? html`<span class="decision-reason"
              >${view.decisionReason.replace(/_/g, " ")}</span
            >`
          : nothing}
      </div>
    `;
  }

  private _renderPrediction(view: ZoneView): TemplateResult | typeof nothing {
    const explanation = view.modelInsight?.decisionExplanation;
    if (!explanation || !explanation.predictedTrajectory.length) return nothing;

    const data = explanation.predictedTrajectory;
    const max = Math.max(...data, view.targetBandHigh ?? view.target ?? 60);
    const min = Math.min(...data, view.targetBandLow ?? 20);
    const range = max - min || 1;
    const h = 60;
    const w = 100;
    const points = data
      .map((v, i) => {
        const x = (i / (data.length - 1)) * w;
        const y = h - ((v - min) / range) * h;
        return `${x},${y}`;
      })
      .join(" ");

    const targetY =
      view.target !== null ? h - ((view.target - min) / range) * h : null;

    return html`
      <div class="prediction-section">
        <div class="section-label">
          Predicted Trajectory
          ${explanation.horizonHours !== null
            ? html`<span class="sublabel">${explanation.horizonHours}h horizon</span>`
            : nothing}
        </div>
        <svg
          class="sparkline"
          viewBox="0 0 ${w} ${h}"
          preserveAspectRatio="none"
        >
          ${targetY !== null
            ? html`<line
                x1="0"
                y1="${targetY}"
                x2="${w}"
                y2="${targetY}"
                class="spark-target"
              />`
            : nothing}
          <polyline points="${points}" class="spark-line" />
        </svg>
        ${explanation.chosenLiters !== null
          ? html`<div class="prediction-note">
              Chosen: ${explanation.chosenLiters} L
              ${explanation.predictedCriticalTheta !== null
                ? html` · Low: ${explanation.predictedCriticalTheta}%`
                : nothing}
              ${explanation.predictedPeakTheta !== null
                ? html` · Peak: ${explanation.predictedPeakTheta}%`
                : nothing}
            </div>`
          : nothing}
      </div>
    `;
  }

  private _renderGreenhouse(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.greenhouse) return nothing;
    return html`
      <div class="info-row greenhouse-row">
        <ha-icon icon="mdi:greenhouse"></ha-icon>
        <span>Greenhouse</span>
        <span class="chip ${view.protectedRain ? "on" : ""}">
          ${view.protectedRain ? "Rain protected" : "Open to rain"}
        </span>
        ${view.temperature !== null
          ? html`<span class="chip">${view.temperature}°C</span>`
          : nothing}
        ${view.humidity !== null
          ? html`<span class="chip">${view.humidity}% RH</span>`
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
    ].filter((c): c is ControlEntity => c !== null);
    const toggles = [
      view.enabledControl,
      view.learningControl,
      view.autoTargetControl,
    ].filter((c): c is ControlEntity => c !== null);
    if (!numbers.length && !toggles.length) return nothing;

    return html`
      <div class="section">
        <div class="section-label">Settings</div>
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
    if (!view.schedule.length) return nothing;
    return html`
      <div class="section">
        <div class="section-label">Schedule</div>
        ${view.schedule.map(
          (slot: ScheduleSlot) => html`
            <div class="row">
              <span
                class="row-label clickable"
                @click=${() => this._moreInfo(slot.timeEntity)}
              >
                <ha-icon icon="mdi:clock-outline" class="row-icon"></ha-icon>
                Slot ${slot.index}
              </span>
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

  private _renderModelInsight(view: ZoneView): TemplateResult | typeof nothing {
    const insight = view.modelInsight;
    if (!insight) return nothing;
    const explanation = insight.decisionExplanation;
    return html`
      <details class="section collapsible">
        <summary class="section-label">
          <span>Model Insight</span>
          ${insight.overallConfidence !== null
            ? html`<span class="confidence-badge"
                >${Math.round(insight.overallConfidence * 100)}%</span
              >`
            : nothing}
        </summary>
        ${insight.bootstrapSummary
          ? html`<div class="note">${insight.bootstrapSummary}</div>`
          : nothing}
        ${explanation?.terms.length
          ? html`
              <div class="terms-grid">
                ${explanation.terms.map(
                  (term) => html`
                    <div class="term ${term.value > 0 ? "gain" : "loss"}">
                      <span class="term-label">${term.label}</span>
                      <span class="term-value"
                        >${term.value > 0 ? "+" : ""}${term.value}${term.unit}</span
                      >
                    </div>
                  `,
                )}
              </div>
            `
          : nothing}
        ${insight.parameters.length
          ? html`
              <div class="params-section">
                ${insight.parameters.map((param) => this._renderParam(param))}
              </div>
            `
          : nothing}
        ${insight.modelUpdated
          ? html`<div class="note">
              Updated ${new Date(insight.modelUpdated).toLocaleString()}
            </div>`
          : nothing}
      </details>
    `;
  }

  private _renderParam(param: ModelParameter): TemplateResult {
    return html`
      <div class="row param-row">
        <span class="row-label">${param.label}</span>
        <span class="row-value">
          ${param.value === null
            ? "learning…"
            : `${param.value} ${param.unit ?? ""}`}
          ${param.confidence !== null
            ? html`<span class="conf-bar">
                <span style="width:${Math.round(param.confidence * 100)}%"></span>
              </span>`
            : nothing}
        </span>
      </div>
    `;
  }

  private _renderReferences(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.references.length) return nothing;
    return html`
      <details class="section collapsible">
        <summary class="section-label">Sensors</summary>
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
      </details>
    `;
  }

  private _renderHistory(view: ZoneView): TemplateResult | typeof nothing {
    if (!view.historyEntries.length) return nothing;
    const recent = view.historyEntries.slice(0, 5);
    return html`
      <details class="section collapsible">
        <summary class="section-label">
          History
          <span class="badge-count">${view.historyCount}</span>
        </summary>
        <div class="history-list">
          ${recent.map((entry) => {
            const kind = String(entry["kind"] ?? "");
            return html`
              <div class="history-entry">
                <span class="history-kind">${KIND_LABELS[kind] ?? kind}</span>
                <span class="history-detail">${this._historyDetail(entry)}</span>
              </div>
            `;
          })}
        </div>
      </details>
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
      <span class="metric-value">${value}</span>
      <span class="metric-label">${label}</span>
    </div>`;
  }

  public static styles = css`
    /* ── Card base ──────────────────────────────────── */
    ha-card {
      padding: 16px;
      overflow: hidden;
    }
    .card-header {
      font-size: 1.1rem;
      font-weight: 600;
      padding-bottom: 12px;
    }

    /* ── Overview Grid ─────────────────────────────── */
    .zone-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }
    .zone-tile {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      padding: 16px 12px 12px;
      border-radius: 12px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color, var(--ha-card-background, #fff));
      cursor: pointer;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
      position: relative;
      overflow: hidden;
      font-family: inherit;
      font-size: inherit;
      color: inherit;
      text-align: center;
    }
    .zone-tile:hover {
      border-color: var(--primary-color);
      box-shadow: 0 2px 8px rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
    }
    .zone-tile:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }
    .zone-tile.watering {
      border-color: var(--state-active-color, var(--primary-color));
    }
    .zone-tile.skip {
      opacity: 0.7;
    }
    .tile-icon-wrap {
      position: relative;
      --mdc-icon-size: 28px;
      color: var(--primary-text-color);
    }
    .zone-tile.watering .tile-icon-wrap {
      color: var(--state-active-color, var(--primary-color));
    }
    .tile-pulse {
      position: absolute;
      inset: -4px;
      border-radius: 50%;
      border: 2px solid var(--state-active-color, var(--primary-color));
      animation: pulse 1.5s ease-out infinite;
    }
    @keyframes pulse {
      0% { transform: scale(0.8); opacity: 1; }
      100% { transform: scale(1.4); opacity: 0; }
    }
    @media (prefers-reduced-motion: reduce) {
      .tile-pulse { animation: none; opacity: 0.5; }
    }
    .tile-name {
      font-size: 0.8rem;
      font-weight: 600;
      line-height: 1.2;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .tile-bar-track {
      width: 100%;
      height: 4px;
      border-radius: 2px;
      background: var(--divider-color);
      position: relative;
      overflow: visible;
    }
    .tile-bar-fill {
      height: 100%;
      border-radius: 2px;
      background: var(--primary-color);
      transition: width 0.4s ease;
    }
    .zone-tile.watering .tile-bar-fill {
      background: var(--state-active-color, var(--primary-color));
    }
    .tile-bar-target {
      position: absolute;
      top: -2px;
      width: 2px;
      height: 8px;
      background: var(--secondary-text-color);
      border-radius: 1px;
      transform: translateX(-50%);
    }
    .tile-stats {
      display: flex;
      gap: 3px;
      font-size: 0.75rem;
      color: var(--secondary-text-color);
    }
    .tile-moisture {
      font-weight: 600;
      color: var(--primary-text-color);
    }

    /* ── Detail View ───────────────────────────────── */
    .detail-card {
      padding: 0;
    }
    .detail-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .back-btn {
      background: none;
      border: none;
      cursor: pointer;
      color: var(--primary-text-color);
      padding: 4px;
      border-radius: 50%;
      display: flex;
      --mdc-icon-size: 20px;
    }
    .back-btn:hover {
      background: var(--secondary-background-color);
    }
    .detail-icon {
      --mdc-icon-size: 24px;
      color: var(--primary-color);
    }
    .detail-title {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
    }
    .detail-name {
      font-size: 1rem;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .detail-status {
      font-size: 0.8rem;
      color: var(--secondary-text-color);
      text-transform: capitalize;
    }
    .detail-status.active {
      color: var(--state-active-color, var(--primary-color));
      font-weight: 600;
    }

    /* ── Moisture Section ──────────────────────────── */
    .moisture-section {
      padding: 16px;
    }
    .moisture-gauge {
      margin-bottom: 12px;
    }
    .gauge-labels {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 8px;
    }
    .gauge-current {
      font-size: 1.8rem;
      font-weight: 700;
      line-height: 1;
    }
    .gauge-sublabel {
      font-size: 0.8rem;
      color: var(--secondary-text-color);
    }
    .gauge-bar-wrap {
      position: relative;
    }
    .gauge-bar-track {
      width: 100%;
      height: 8px;
      border-radius: 4px;
      background: var(--divider-color);
      position: relative;
      overflow: visible;
    }
    .gauge-fill {
      height: 100%;
      border-radius: 4px;
      background: var(--primary-color);
      transition: width 0.5s ease;
    }
    .gauge-target-band {
      position: absolute;
      top: 0;
      height: 100%;
      background: var(--primary-color);
      opacity: 0.15;
      border-radius: 4px;
    }
    .gauge-target-line {
      position: absolute;
      top: -3px;
      width: 2px;
      height: 14px;
      background: var(--secondary-text-color);
      border-radius: 1px;
      transform: translateX(-50%);
    }
    .gauge-marker {
      position: absolute;
      top: -4px;
      width: 10px;
      height: 10px;
      background: var(--primary-color);
      border: 2px solid var(--card-background-color, #fff);
      border-radius: 50%;
      transform: translate(-50%, 3px);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    }
    .gauge-ticks {
      display: flex;
      justify-content: space-between;
      font-size: 0.65rem;
      color: var(--secondary-text-color);
      margin-top: 4px;
      position: relative;
    }
    .gauge-ticks span {
      position: relative;
    }

    .metric-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .metric {
      display: flex;
      flex-direction: column;
      align-items: center;
      flex: 1;
      min-width: 70px;
      padding: 8px 6px;
      background: var(--secondary-background-color);
      border-radius: 8px;
    }
    .metric-value {
      font-size: 0.9rem;
      font-weight: 600;
    }
    .metric-label {
      font-size: 0.7rem;
      color: var(--secondary-text-color);
    }

    /* ── Decision Banner ───────────────────────────── */
    .decision-banner {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      font-size: 0.85rem;
    }
    .decision-banner.water {
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
    }
    .decision-banner.skip {
      background: var(--secondary-background-color);
    }
    .decision-label {
      font-weight: 600;
      text-transform: capitalize;
    }
    .decision-reason {
      color: var(--secondary-text-color);
      font-size: 0.8rem;
    }

    /* ── Prediction Sparkline ──────────────────────── */
    .prediction-section {
      padding: 8px 16px 12px;
    }
    .sparkline {
      width: 100%;
      height: 48px;
      display: block;
    }
    .spark-line {
      fill: none;
      stroke: var(--primary-color);
      stroke-width: 1.5;
      vector-effect: non-scaling-stroke;
    }
    .spark-target {
      stroke: var(--secondary-text-color);
      stroke-width: 0.5;
      stroke-dasharray: 3 2;
      vector-effect: non-scaling-stroke;
    }
    .prediction-note {
      font-size: 0.75rem;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }

    /* ── Sections ──────────────────────────────────── */
    .section {
      padding: 0 16px 12px;
    }
    .section-label {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--secondary-text-color);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .sublabel {
      font-weight: 400;
      opacity: 0.7;
    }
    .collapsible {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      margin: 0 16px 12px;
      padding: 10px 12px;
    }
    .collapsible summary {
      cursor: pointer;
      list-style: none;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .collapsible summary::-webkit-details-marker { display: none; }
    .collapsible[open] summary {
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--divider-color);
    }

    /* ── Shared Rows ───────────────────────────────── */
    .row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.82rem;
      padding: 5px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .row:last-child { border-bottom: none; }
    .row-label { flex: 1; display: flex; align-items: center; gap: 4px; }
    .row-icon { --mdc-icon-size: 16px; opacity: 0.6; }
    .row-value { color: var(--secondary-text-color); text-align: right; }
    .clickable { cursor: pointer; }
    .clickable:hover { color: var(--primary-color); }
    .toggle {
      border: 1px solid var(--divider-color);
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
      border-radius: 12px;
      padding: 2px 10px;
      font-size: 0.72rem;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
    }
    .toggle.on {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      border-color: var(--primary-color);
    }

    /* ── Info Row (greenhouse) ─────────────────────── */
    .info-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      font-size: 0.82rem;
      --mdc-icon-size: 18px;
    }
    .chip {
      font-size: 0.72rem;
      padding: 2px 8px;
      border-radius: 10px;
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
    }
    .chip.on { color: var(--primary-color); font-weight: 600; }

    /* ── Model Insight ─────────────────────────────── */
    .confidence-badge {
      font-size: 0.72rem;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 8px;
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
    }
    .note {
      font-size: 0.75rem;
      color: var(--secondary-text-color);
      margin: 4px 0;
    }
    .terms-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px;
      margin: 6px 0;
    }
    .term {
      display: flex;
      justify-content: space-between;
      font-size: 0.78rem;
      padding: 4px 8px;
      border-radius: 6px;
      background: var(--secondary-background-color);
    }
    .term.gain .term-value { color: var(--label-badge-green, #4caf50); }
    .term.loss .term-value { color: var(--error-color, #db4437); }
    .conf-bar {
      display: inline-block;
      width: 36px;
      height: 5px;
      background: var(--divider-color);
      border-radius: 3px;
      overflow: hidden;
      vertical-align: middle;
      margin-left: 4px;
    }
    .conf-bar span {
      display: block;
      height: 100%;
      background: var(--primary-color);
    }
    .badge-count {
      font-size: 0.7rem;
      background: var(--secondary-background-color);
      padding: 1px 6px;
      border-radius: 8px;
    }

    /* ── History ────────────────────────────────────── */
    .history-list {
      display: flex;
      flex-direction: column;
    }
    .history-entry {
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      padding: 4px 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .history-entry:last-child { border-bottom: none; }
    .history-kind { font-weight: 500; }
    .history-detail { color: var(--secondary-text-color); }

    /* ── Actions ────────────────────────────────────── */
    .detail-actions {
      display: flex;
      gap: 8px;
      padding: 12px 16px;
      border-top: 1px solid var(--divider-color);
    }
    .stop-btn {
      --mdc-theme-primary: var(--error-color);
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "amazing-irrigation-overview-card": AmazingIrrigationOverviewCard;
  }
  interface Window {
    customCards?: Array<Record<string, unknown>>;
  }
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "amazing-irrigation-overview-card",
  name: "Amazing Irrigation",
  description:
    "Professional irrigation dashboard with zone overview and detail drill-down.",
});
