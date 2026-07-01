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

/** Plain-language rewrites for machine decision reasons. */
const REASON_LABELS: Record<string, string> = {
  predicted_sufficient_moisture: "Soil moisture is on track",
  sufficient_moisture: "Soil moisture is on track",
  rain_expected: "Rain expected, holding off",
  rain_protected: "Sheltered from rain",
  below_target: "Below target, watering needed",
  schedule: "On schedule",
  manual: "Manual run",
  forced: "Forced by you",
  learning: "Still learning this zone",
};

function humanizeReason(reason: string): string {
  return REASON_LABELS[reason] ?? reason.replace(/_/g, " ");
}

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

/** Turn a timestamp into a short relative label ("2h ago"). */
function relativeTime(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const ms = typeof value === "number" ? value * (value < 1e12 ? 1000 : 1) : Date.parse(String(value));
  if (!Number.isFinite(ms)) return null;
  const diff = Date.now() - ms;
  if (diff < 0) return "soon";
  const m = Math.round(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return d < 7 ? `${d}d ago` : new Date(ms).toLocaleDateString();
}

const DEFAULT_ZONE_ICON = "mdi:sprinkler-variant";

@customElement("amazing-irrigation-overview-card")
export class AmazingIrrigationOverviewCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: OverviewCardConfig;
  @state() private _activeZoneIndex: number | null = null;
  @state() private _actionPending: string | null = null;
  @state() private _actionResult: { kind: "ok" | "error"; text: string } | null =
    null;
  @state() private _forceArmed = false;

  private _actionResultTimer?: ReturnType<typeof setTimeout>;
  private _forceArmTimer?: ReturnType<typeof setTimeout>;
  private _lastFailed?: { entity: string; service: "run_zone" | "stop_zone"; force: boolean };

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
    this._disarmForce();
    this._actionResult = null;
  }

  private _closeZone(): void {
    this._activeZoneIndex = null;
    this._disarmForce();
  }

  private _disarmForce(): void {
    this._forceArmed = false;
    if (this._forceArmTimer) clearTimeout(this._forceArmTimer);
  }

  private _armForce(): void {
    this._forceArmed = true;
    if (this._forceArmTimer) clearTimeout(this._forceArmTimer);
    this._forceArmTimer = setTimeout(() => {
      this._forceArmed = false;
    }, 5000);
  }

  private async _callZoneService(
    decisionEntity: string,
    service: "run_zone" | "stop_zone",
    force = false,
  ) {
    if (!this.hass || this._actionPending) return;
    const actionKey =
      service === "stop_zone" ? "stop" : force ? "force" : "run";
    this._actionPending = actionKey;
    this._actionResult = null;
    this._disarmForce();
    if (this._actionResultTimer) clearTimeout(this._actionResultTimer);

    const data: Record<string, unknown> = { entity_id: decisionEntity };
    if (service === "run_zone") data.force = force;

    try {
      await this.hass.callService("amazing_irrigation", service, data);
      const label =
        actionKey === "stop"
          ? "Stop sent"
          : force
            ? "Force sent"
            : "Run sent";
      this._actionResult = { kind: "ok", text: label };
      this._lastFailed = undefined;
      this._actionResultTimer = setTimeout(() => {
        this._actionResult = null;
      }, 4000);
    } catch (err) {
      const detail =
        err instanceof Error && err.message ? err.message : "Service unavailable";
      this._actionResult = { kind: "error", text: detail };
      this._lastFailed = { entity: decisionEntity, service, force };
      this._actionResultTimer = setTimeout(() => {
        this._actionResult = null;
      }, 8000);
    } finally {
      this._actionPending = null;
    }
  }

  private _retryLast(): void {
    if (this._lastFailed) {
      const { entity, service, force } = this._lastFailed;
      this._callZoneService(entity, service, force);
    }
  }

  private async _runAll(): Promise<void> {
    if (!this.hass || !this._config || this._actionPending) return;
    this._actionPending = "all";
    this._actionResult = null;
    if (this._actionResultTimer) clearTimeout(this._actionResultTimer);
    let ok = 0;
    let fail = 0;
    for (const zone of this._config.zones) {
      try {
        await this.hass.callService("amazing_irrigation", "run_zone", {
          entity_id: zone.decision_entity,
          force: false,
        });
        ok += 1;
      } catch {
        fail += 1;
      }
    }
    this._actionResult = {
      kind: fail ? "error" : "ok",
      text: fail ? `${ok} run, ${fail} failed` : `Run sent to ${ok} zones`,
    };
    this._actionPending = null;
    this._actionResultTimer = setTimeout(() => {
      this._actionResult = null;
    }, fail ? 8000 : 4000);
  }

  private _quickRun(e: Event, index: number): void {
    e.stopPropagation();
    const zone = this._config?.zones[index];
    if (zone) this._callZoneService(zone.decision_entity, "run_zone");
  }

  public disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._actionResultTimer) clearTimeout(this._actionResultTimer);
    if (this._forceArmTimer) clearTimeout(this._forceArmTimer);
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
    const multi = views.length > 1;
    return html`
      <ha-card>
        <div class="overview-header">
          ${this._config!.title
            ? html`<div class="card-header">${this._config!.title}</div>`
            : html`<span></span>`}
          ${multi
            ? html`<button
                class="run-all-btn"
                title="Run every zone the model allows"
                ?disabled=${!!this._actionPending}
                @click=${this._runAll}
              >
                ${this._actionPending === "all"
                  ? html`<ha-circular-progress
                      indeterminate
                      size="small"
                    ></ha-circular-progress>`
                  : html`<ha-icon icon="mdi:play-circle-outline"></ha-icon>`}
                Run all
              </button>`
            : nothing}
        </div>
        ${this._actionResult
          ? html`<div class="action-feedback overview ${this._actionResult.kind}">
              <ha-icon
                icon=${this._actionResult.kind === "ok"
                  ? "mdi:check-circle-outline"
                  : "mdi:alert-circle-outline"}
              ></ha-icon>
              ${this._actionResult.text}
            </div>`
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
    const noData = view.moisture === null && view.decision === null;
    const moisturePct =
      view.moisture !== null && view.target !== null && view.target > 0
        ? Math.min(100, Math.round((view.moisture / view.target) * 100))
        : view.moisture ?? 0;

    const statusClass = noData
      ? "setup"
      : view.isWatering
        ? "watering"
        : view.decision === "skip"
          ? "skip"
          : view.decision === "water"
            ? "pending-water"
            : "";

    return html`
      <button
        class="zone-tile ${statusClass}"
        title="Open ${view.name}"
        @click=${() => this._openZone(index)}
      >
        <div class="tile-icon-wrap">
          <ha-icon .icon=${icon}></ha-icon>
          ${view.isWatering
            ? html`<span class="tile-pulse"></span>`
            : nothing}
        </div>
        <span class="tile-name">${view.name}</span>
        ${noData
          ? html`<span class="tile-setup">Setting up…</span>`
          : html`
              <div class="tile-bar-track">
                <div class="tile-bar-fill" style="width: ${moisturePct}%"></div>
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
            `}
        ${noData
          ? nothing
          : html`<span
              class="tile-run"
              title="Run ${view.name} now"
              ?disabled=${!!this._actionPending}
              @click=${(e: Event) => this._quickRun(e, index)}
            >
              <ha-icon icon="mdi:play"></ha-icon>
            </span>`}
      </button>
    `;
  }

  /* ─── Detail View ───────────────────────────────────────────── */

  private _renderDetail(
    view: ZoneView,
    config: ZoneCardConfig,
  ): TemplateResult {
    const noData =
      view.moisture === null &&
      view.decision === null &&
      !view.modelInsight?.decisionExplanation?.predictedTrajectory.length;
    return html`
      <ha-card class="detail-card">
        <div class="detail-header">
          <button class="back-btn" title="Back to all zones" @click=${this._closeZone}>
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

        ${noData
          ? html`<div class="onboarding">
              <ha-icon icon="mdi:leaf-circle-outline"></ha-icon>
              <div class="onboarding-text">
                <strong>Getting to know this zone</strong>
                <span
                  >No moisture data yet. The model needs a few days of readings
                  before it can predict and schedule. You can still
                  <em>Run</em> the zone manually below.</span
                >
              </div>
            </div>`
          : nothing}

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
            title="Water now, respecting the model's recommended amount"
            ?disabled=${!canRun(view) || !!this._actionPending}
            @click=${() =>
              this._callZoneService(config.decision_entity, "run_zone")}
          >
            ${this._actionPending === "run"
              ? html`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`
              : html`<ha-icon icon="mdi:play" slot="icon"></ha-icon>`}
            Run
          </mwc-button>
          <mwc-button
            class="force-btn ${this._forceArmed ? "armed" : ""}"
            title="Override the model and water regardless of conditions"
            ?disabled=${!canRun(view) || !!this._actionPending}
            @click=${() => {
              if (this._forceArmed) {
                this._callZoneService(config.decision_entity, "run_zone", true);
              } else {
                this._armForce();
              }
            }}
          >
            ${this._actionPending === "force"
              ? html`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`
              : html`<ha-icon
                  icon=${this._forceArmed ? "mdi:alert" : "mdi:water"}
                  slot="icon"
                ></ha-icon>`}
            ${this._forceArmed ? "Confirm Force" : "Force"}
          </mwc-button>
          ${canStop(view)
            ? html`<mwc-button
                class="stop-btn"
                title="Stop the current watering run"
                ?disabled=${!!this._actionPending}
                @click=${() =>
                  this._callZoneService(config.decision_entity, "stop_zone")}
              >
                ${this._actionPending === "stop"
                  ? html`<ha-circular-progress indeterminate size="small"></ha-circular-progress>`
                  : html`<ha-icon icon="mdi:stop" slot="icon"></ha-icon>`}
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
                ${this._actionResult.kind === "error" && this._lastFailed
                  ? html`<button class="retry-btn" @click=${this._retryLast}>
                      Retry
                    </button>`
                  : nothing}
              </span>`
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
              >${humanizeReason(view.decisionReason)}</span
            >`
          : nothing}
      </div>
    `;
  }

  private _renderPrediction(view: ZoneView): TemplateResult | typeof nothing {
    const explanation = view.modelInsight?.decisionExplanation;
    if (!explanation || !explanation.predictedTrajectory.length) return nothing;

    const data = explanation.predictedTrajectory;
    const horizonH = explanation.horizonHours ?? data.length;
    const hoursPerSlot = data.length > 1 ? horizonH / (data.length - 1) : 1;

    const bandLow = view.targetBandLow ?? (view.target !== null ? view.target - 2 : null);
    const bandHigh = view.targetBandHigh ?? (view.target !== null ? view.target + 2 : null);

    const dataMin = Math.min(...data);
    const dataMax = Math.max(...data);
    const yMin = Math.floor(Math.min(dataMin, bandLow ?? dataMin, 0) / 5) * 5;
    const yMax = Math.ceil(Math.max(dataMax, bandHigh ?? dataMax, view.target ?? 0) / 5) * 5 + 5;
    const yRange = yMax - yMin || 1;

    const padL = 32;
    const padR = 8;
    const padT = 12;
    const padB = 24;
    const chartW = 300;
    const chartH = 100;
    const totalW = chartW + padL + padR;
    const totalH = chartH + padT + padB;

    const toX = (i: number) => padL + (i / (data.length - 1)) * chartW;
    const toY = (v: number) => padT + chartH - ((v - yMin) / yRange) * chartH;

    const linePath = data
      .map((v, i) => `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(v).toFixed(1)}`)
      .join(" ");

    const fillPath =
      linePath +
      ` L${toX(data.length - 1).toFixed(1)},${toY(yMin).toFixed(1)}` +
      ` L${toX(0).toFixed(1)},${toY(yMin).toFixed(1)} Z`;

    const yTicks: number[] = [];
    const step = yRange <= 30 ? 5 : yRange <= 60 ? 10 : 20;
    for (let v = yMin; v <= yMax; v += step) yTicks.push(v);

    const xLabels: Array<{ i: number; label: string }> = [];
    const labelStep = data.length <= 8 ? 1 : data.length <= 16 ? 2 : Math.ceil(data.length / 8);
    for (let i = 0; i < data.length; i += labelStep) {
      xLabels.push({ i, label: `+${Math.round(i * hoursPerSlot)}h` });
    }
    if (xLabels[xLabels.length - 1]?.i !== data.length - 1) {
      xLabels.push({ i: data.length - 1, label: `+${Math.round(horizonH)}h` });
    }

    const criticalTheta = explanation.predictedCriticalTheta;
    const peakTheta = explanation.predictedPeakTheta;
    const criticalIdx = criticalTheta !== null
      ? data.indexOf(Math.min(...data))
      : null;
    const peakIdx = peakTheta !== null
      ? data.indexOf(Math.max(...data))
      : null;

    return html`
      <div class="prediction-section">
        <div class="section-label">
          Moisture Prediction
          <ha-icon
            class="help-dot"
            icon="mdi:help-circle-outline"
            title="Forecast soil moisture over the coming hours. Shaded band is the target range; dots are the critical low and peak."
          ></ha-icon>
          ${explanation.horizonHours !== null
            ? html`<span class="sublabel">${explanation.horizonHours}h horizon</span>`
            : nothing}
        </div>

        <svg
          class="prediction-chart"
          viewBox="0 0 ${totalW} ${totalH}"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <linearGradient id="pred-fill-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--primary-color)" stop-opacity="0.18" />
              <stop offset="100%" stop-color="var(--primary-color)" stop-opacity="0.02" />
            </linearGradient>
          </defs>

          <!-- Y-axis gridlines + labels -->
          ${yTicks.map(
            (v) => html`
              <line
                x1="${padL}" y1="${toY(v)}" x2="${padL + chartW}" y2="${toY(v)}"
                class="pred-grid"
              />
              <text x="${padL - 4}" y="${toY(v) + 3}" class="pred-y-label">${v}</text>
            `,
          )}

          <!-- Target band shading -->
          ${bandLow !== null && bandHigh !== null
            ? html`<rect
                x="${padL}" y="${toY(bandHigh)}"
                width="${chartW}" height="${Math.abs(toY(bandLow) - toY(bandHigh))}"
                class="pred-target-band"
              />`
            : nothing}

          <!-- Target line -->
          ${view.target !== null
            ? html`<line
                x1="${padL}" y1="${toY(view.target)}"
                x2="${padL + chartW}" y2="${toY(view.target)}"
                class="pred-target-line"
              />`
            : nothing}

          <!-- Area fill -->
          <path d="${fillPath}" class="pred-area" />

          <!-- Line -->
          <path d="${linePath}" class="pred-line" />

          <!-- Data points -->
          ${data.map(
            (v, i) => html`
              <circle
                cx="${toX(i)}" cy="${toY(v)}" r="2.5"
                class="pred-dot"
              />
            `,
          )}

          <!-- Critical / Peak markers -->
          ${criticalIdx !== null && criticalTheta !== null
            ? html`<circle
                cx="${toX(criticalIdx)}" cy="${toY(data[criticalIdx])}" r="4"
                class="pred-marker-critical"
              />`
            : nothing}
          ${peakIdx !== null && peakTheta !== null
            ? html`<circle
                cx="${toX(peakIdx)}" cy="${toY(data[peakIdx])}" r="4"
                class="pred-marker-peak"
              />`
            : nothing}

          <!-- X-axis labels -->
          ${xLabels.map(
            ({ i, label }) => html`
              <text
                x="${toX(i)}" y="${padT + chartH + 16}"
                class="pred-x-label"
              >${label}</text>
            `,
          )}

          <!-- Current moisture marker (first point) -->
          <text
            x="${toX(0) + 4}" y="${toY(data[0]) - 6}"
            class="pred-value-label"
          >${Math.round(data[0])}%</text>

          <!-- End value label -->
          <text
            x="${toX(data.length - 1) - 4}" y="${toY(data[data.length - 1]) - 6}"
            class="pred-value-label end"
          >${Math.round(data[data.length - 1])}%</text>
        </svg>

        <div class="pred-legend">
          ${view.target !== null
            ? html`<span class="pred-legend-item">
                <span class="pred-swatch target"></span>Target ${view.target}%
              </span>`
            : nothing}
          ${criticalTheta !== null
            ? html`<span class="pred-legend-item">
                <span class="pred-swatch critical"></span>Low ${criticalTheta}%
              </span>`
            : nothing}
          ${peakTheta !== null
            ? html`<span class="pred-legend-item">
                <span class="pred-swatch peak"></span>Peak ${peakTheta}%
              </span>`
            : nothing}
          ${explanation.chosenLiters !== null
            ? html`<span class="pred-legend-item">
                <ha-icon icon="mdi:water" style="--mdc-icon-size:14px"></ha-icon>
                ${explanation.chosenLiters} L
              </span>`
            : nothing}
        </div>

        <!-- Water balance terms breakdown -->
        ${explanation.terms.length
          ? html`<div class="pred-terms">
              ${explanation.terms.map(
                (t) => html`
                  <div class="pred-term">
                    <span class="pred-term-label">${t.label}</span>
                    <span class="pred-term-value ${t.value >= 0 ? "positive" : "negative"}">
                      ${t.value >= 0 ? "+" : ""}${t.value.toFixed(1)}${t.unit}
                    </span>
                  </div>
                `,
              )}
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
    if (!numbers.length && !toggles.length && !selects.length) return nothing;

    return html`
      <div class="section">
        <div class="section-label">Settings</div>
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
            ? html`<span
                class="confidence-badge ${this._confLevel(insight.overallConfidence)}"
                title="How confident the model is in its prediction for this zone"
                ><span class="conf-meter" aria-hidden="true"
                  ><i></i><i></i><i></i
                ></span>
                <span class="conf-word"
                  >${this._confWord(insight.overallConfidence)}</span
                >
                <span class="conf-pct"
                  >${Math.round(insight.overallConfidence * 100)}%</span
                ></span
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

  private _confLevel(c: number): "conf-low" | "conf-med" | "conf-high" {
    if (c >= 0.8) return "conf-high";
    if (c >= 0.5) return "conf-med";
    return "conf-low";
  }

  private _confWord(c: number): string {
    if (c >= 0.8) return "High";
    if (c >= 0.5) return "Medium";
    return "Low";
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
            ? html`<span class="conf-bar ${this._confLevel(param.confidence)}">
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
            const when = relativeTime(
              entry["timestamp"] ?? entry["ts"] ?? entry["time"] ?? entry["when"],
            );
            return html`
              <div class="history-entry">
                <span class="history-kind">${KIND_LABELS[kind] ?? kind}</span>
                <span class="history-detail">${this._historyDetail(entry)}</span>
                ${when
                  ? html`<span class="history-time">${when}</span>`
                  : nothing}
              </div>
            `;
          })}
        </div>
      </details>
    `;
  }

  private _historyDetail(entry: Record<string, unknown>): string {
    if (entry["action"]) {
      return `${entry["action"]} (${humanizeReason(String(entry["reason"] ?? ""))})`;
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

    /* ── Prediction Chart ─────────────────────────── */
    .prediction-section {
      padding: 8px 16px 12px;
    }
    .prediction-chart {
      width: 100%;
      height: auto;
      max-height: 160px;
      display: block;
    }
    .pred-grid {
      stroke: var(--divider-color, rgba(255,255,255,0.08));
      stroke-width: 0.5;
      vector-effect: non-scaling-stroke;
    }
    .pred-y-label {
      font-size: 7px;
      fill: var(--secondary-text-color);
      text-anchor: end;
      dominant-baseline: middle;
    }
    .pred-x-label {
      font-size: 7px;
      fill: var(--secondary-text-color);
      text-anchor: middle;
    }
    .pred-target-band {
      fill: var(--primary-color);
      opacity: 0.08;
    }
    .pred-target-line {
      stroke: var(--primary-color);
      stroke-width: 0.8;
      stroke-dasharray: 4 2;
      vector-effect: non-scaling-stroke;
      opacity: 0.5;
    }
    .pred-area {
      fill: url(#pred-fill-grad);
    }
    .pred-line {
      fill: none;
      stroke: var(--primary-color);
      stroke-width: 1.8;
      stroke-linejoin: round;
      stroke-linecap: round;
      vector-effect: non-scaling-stroke;
    }
    .pred-dot {
      fill: var(--card-background-color, var(--primary-background-color));
      stroke: var(--primary-color);
      stroke-width: 1;
      vector-effect: non-scaling-stroke;
    }
    .pred-marker-critical {
      fill: none;
      stroke: var(--error-color, #db4437);
      stroke-width: 1.5;
      vector-effect: non-scaling-stroke;
    }
    .pred-marker-peak {
      fill: none;
      stroke: var(--success-color, #43a047);
      stroke-width: 1.5;
      vector-effect: non-scaling-stroke;
    }
    .pred-value-label {
      font-size: 7px;
      font-weight: 600;
      fill: var(--primary-text-color);
      text-anchor: start;
    }
    .pred-value-label.end {
      text-anchor: end;
    }

    .pred-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 4px 0 0;
      font-size: 0.72rem;
      color: var(--secondary-text-color);
    }
    .pred-legend-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .pred-swatch {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .pred-swatch.target {
      background: var(--primary-color);
      opacity: 0.5;
    }
    .pred-swatch.critical {
      border: 1.5px solid var(--error-color, #db4437);
      background: none;
    }
    .pred-swatch.peak {
      border: 1.5px solid var(--success-color, #43a047);
      background: none;
    }

    .pred-terms {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 4px 12px;
      padding: 8px 0 0;
      font-size: 0.75rem;
    }
    .pred-term {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .pred-term-label {
      color: var(--secondary-text-color);
    }
    .pred-term-value {
      font-weight: 500;
      font-variant-numeric: tabular-nums;
    }
    .pred-term-value.positive {
      color: var(--success-color, #43a047);
    }
    .pred-term-value.negative {
      color: var(--error-color, #db4437);
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
    .row.warning { color: var(--warning-color, #ff9800); font-size: 0.78rem; align-items: flex-start; }
    .row.warning ha-icon { --mdc-icon-size: 18px; flex: 0 0 auto; }
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
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 0.7rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 999px;
      font-variant-numeric: tabular-nums;
      --conf: var(--primary-color);
      background: color-mix(in srgb, var(--conf) 16%, transparent);
      color: color-mix(in srgb, var(--conf) 72%, var(--primary-text-color));
    }
    .confidence-badge.conf-high { --conf: var(--success-color, #43a047); }
    .confidence-badge.conf-med  { --conf: var(--warning-color, #ff9800); }
    .confidence-badge.conf-low  { --conf: var(--error-color, #db4437); }
    .conf-word { letter-spacing: 0.01em; }
    .conf-pct { opacity: 0.75; font-weight: 700; }
    .conf-meter { display: inline-flex; gap: 2px; }
    .conf-meter i {
      width: 4px; height: 9px; border-radius: 1px;
      background: color-mix(in srgb, var(--conf) 22%, var(--divider-color));
    }
    .confidence-badge.conf-low .conf-meter i:nth-child(1),
    .confidence-badge.conf-med .conf-meter i:nth-child(-n + 2),
    .confidence-badge.conf-high .conf-meter i { background: var(--conf); }
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
    .conf-bar.conf-high span { background: var(--success-color, #43a047); }
    .conf-bar.conf-med span  { background: var(--warning-color, #ff9800); }
    .conf-bar.conf-low span  { background: var(--error-color, #db4437); }
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
      align-items: center;
      flex-wrap: wrap;
    }
    .detail-actions mwc-button[disabled] {
      opacity: 0.5;
      pointer-events: none;
    }
    .detail-actions ha-circular-progress {
      --mdc-theme-primary: currentColor;
      margin-inline-end: 4px;
    }
    .stop-btn {
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
    .action-feedback.overview {
      margin-top: 12px;
    }
    .retry-btn {
      --mdc-theme-primary: var(--error-color);
    }

    /* ── Overview header / Run-All ──────────────────── */
    .overview-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding-bottom: 12px;
    }
    .run-all-btn {
      --mdc-theme-primary: var(--primary-color);
    }
    .run-all-btn ha-circular-progress {
      --mdc-theme-primary: currentColor;
      margin-inline-end: 4px;
    }

    /* ── Tile quick-run ─────────────────────────────── */
    .tile-run {
      position: absolute;
      top: 6px;
      right: 6px;
      --mdc-icon-button-size: 28px;
      --mdc-icon-size: 18px;
      color: var(--secondary-text-color);
      opacity: 0;
      transition: opacity 0.15s ease, color 0.15s ease;
    }
    .zone-tile:hover .tile-run,
    .zone-tile:focus-within .tile-run {
      opacity: 1;
    }
    .tile-run:hover {
      color: var(--primary-color);
    }
    .tile-setup {
      font-size: 0.72rem;
      color: var(--secondary-text-color);
    }

    /* ── Onboarding banner ──────────────────────────── */
    .onboarding {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      padding: 12px 14px;
      margin: 12px 16px;
      border-radius: 12px;
      border: 1px solid var(--divider-color);
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.06);
      font-size: 0.85rem;
      line-height: 1.4;
    }
    .onboarding ha-icon {
      color: var(--primary-color);
      flex-shrink: 0;
    }
    .onboarding b { font-weight: 600; }

    /* ── Force two-tap ──────────────────────────────── */
    .force-btn.armed {
      --mdc-theme-primary: var(--warning-color, #ff9800);
    }
    .help-dot {
      --mdc-icon-size: 15px;
      color: var(--secondary-text-color);
      cursor: help;
      margin-inline-start: 4px;
      vertical-align: middle;
    }
    .history-time {
      color: var(--secondary-text-color);
      font-variant-numeric: tabular-nums;
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
