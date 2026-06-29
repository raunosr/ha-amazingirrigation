import { LitElement, html, css, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import type { OverviewCardConfig, ZoneCardConfig } from "./zone-view";

/**
 * Minimal Home Assistant shape needed by the editors. The real `hass` object is
 * passed through to `ha-form`, which renders the entity pickers and inputs.
 */
interface HomeAssistant {
  states: Record<string, unknown>;
}

interface HaFormSchema {
  name: string;
  required?: boolean;
  selector: Record<string, unknown>;
}

const INTEGRATION = "amazing_irrigation";

// Our integration's per-zone sensors are filtered to this integration; the
// soil-moisture sensor is the user's own (e.g. Ecowitt), so it stays generic.
const ZONE_SCHEMA: HaFormSchema[] = [
  {
    name: "decision_entity",
    required: true,
    selector: { entity: { integration: INTEGRATION, domain: "sensor" } },
  },
  { name: "name", selector: { text: {} } },
  { name: "icon", selector: { icon: {} } },
  { name: "moisture_entity", selector: { entity: { domain: "sensor" } } },
  {
    name: "status_entity",
    selector: { entity: { integration: INTEGRATION, domain: "sensor" } },
  },
  {
    name: "history_entity",
    selector: { entity: { integration: INTEGRATION, domain: "sensor" } },
  },
];

const TITLE_SCHEMA: HaFormSchema[] = [
  { name: "title", selector: { text: {} } },
];

const LABELS: Record<string, string> = {
  decision_entity: "Decision sensor (required)",
  name: "Zone name (optional)",
  icon: "Zone icon (optional)",
  moisture_entity: "Soil moisture sensor (optional)",
  status_entity: "Status sensor (optional)",
  history_entity: "History sensor (optional)",
  title: "Card title (optional)",
};

const computeLabel = (schema: HaFormSchema): string =>
  LABELS[schema.name] ?? schema.name;

function fireConfigChanged(node: HTMLElement, config: unknown): void {
  node.dispatchEvent(
    new CustomEvent("config-changed", {
      detail: { config },
      bubbles: true,
      composed: true,
    }),
  );
}

@customElement("amazing-irrigation-card-editor")
export class AmazingIrrigationCardEditor extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: ZoneCardConfig;

  public setConfig(config: ZoneCardConfig): void {
    this._config = config;
  }

  protected render(): TemplateResult | typeof nothing {
    if (!this.hass || !this._config) {
      return nothing;
    }
    return html`
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${ZONE_SCHEMA}
        .computeLabel=${computeLabel}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `;
  }

  private _valueChanged(ev: CustomEvent): void {
    ev.stopPropagation();
    fireConfigChanged(this, ev.detail.value);
  }
}

@customElement("amazing-irrigation-overview-card-editor")
export class AmazingIrrigationOverviewCardEditor extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: OverviewCardConfig;

  public setConfig(config: OverviewCardConfig): void {
    this._config = {
      ...config,
      zones: Array.isArray(config.zones) ? config.zones : [],
    };
  }

  private get _zones(): ZoneCardConfig[] {
    return this._config?.zones ?? [];
  }

  protected render(): TemplateResult | typeof nothing {
    if (!this.hass || !this._config) {
      return nothing;
    }
    return html`
      <div class="editor">
        <ha-form
          .hass=${this.hass}
          .data=${{ title: this._config.title ?? "" }}
          .schema=${TITLE_SCHEMA}
          .computeLabel=${computeLabel}
          @value-changed=${this._titleChanged}
        ></ha-form>

        <div class="zones">
          ${this._zones.map((zone, index) => this._renderZone(zone, index))}
          ${this._zones.length === 0
            ? html`<div class="hint">
                Add at least one zone (select its Decision sensor).
              </div>`
            : nothing}
        </div>

        <mwc-button outlined @click=${this._addZone}>+ Add zone</mwc-button>
      </div>
    `;
  }

  private _renderZone(zone: ZoneCardConfig, index: number): TemplateResult {
    return html`
      <div class="zone">
        <div class="zone-head">
          <span class="zone-title">Zone ${index + 1}</span>
          <mwc-button dense @click=${() => this._removeZone(index)}>
            Remove
          </mwc-button>
        </div>
        <ha-form
          .hass=${this.hass}
          .data=${zone}
          .schema=${ZONE_SCHEMA}
          .computeLabel=${computeLabel}
          .index=${index}
          @value-changed=${this._zoneChanged}
        ></ha-form>
      </div>
    `;
  }

  private _titleChanged(ev: CustomEvent): void {
    ev.stopPropagation();
    const title = (ev.detail.value as { title?: string }).title;
    const config: OverviewCardConfig = { ...this._config!, title };
    if (!title) {
      delete config.title;
    }
    this._emit(config);
  }

  private _zoneChanged(ev: CustomEvent): void {
    ev.stopPropagation();
    const index = (ev.currentTarget as HTMLElement & { index?: number }).index;
    if (index === undefined) {
      return;
    }
    const zones = [...this._zones];
    zones[index] = ev.detail.value as ZoneCardConfig;
    this._emit({ ...this._config!, zones });
  }

  private _addZone(): void {
    const zones = [
      ...this._zones,
      { decision_entity: "" } as ZoneCardConfig,
    ];
    this._emit({ ...this._config!, zones });
  }

  private _removeZone(index: number): void {
    const zones = this._zones.filter((_, i) => i !== index);
    this._emit({ ...this._config!, zones });
  }

  private _emit(config: OverviewCardConfig): void {
    this._config = config;
    fireConfigChanged(this, config);
  }

  public static styles = css`
    .editor {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .zones {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .zone {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      padding: 12px;
    }
    .zone-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .zone-title {
      font-weight: 600;
    }
    .hint {
      color: var(--secondary-text-color);
      font-size: 0.9rem;
    }
    mwc-button {
      align-self: flex-start;
    }
  `;
}

declare global {
  interface HTMLElementTagNameMap {
    "amazing-irrigation-card-editor": AmazingIrrigationCardEditor;
    "amazing-irrigation-overview-card-editor": AmazingIrrigationOverviewCardEditor;
  }
}
