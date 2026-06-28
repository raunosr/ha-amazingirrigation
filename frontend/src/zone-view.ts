/**
 * Pure view-model helpers for the Amazing Irrigation zone card.
 *
 * These functions intentionally take plain Home Assistant state objects (not the
 * `hass` object or DOM) so they can be unit-tested without a browser. The card
 * is a thin display/control layer: the integration remains the source of truth,
 * and capability gating (e.g. whether Stop is allowed) is driven by backend
 * state, never assumed by the card.
 */

export interface HassState {
  state: string;
  attributes: Record<string, unknown>;
}

export interface ZoneCardConfig {
  type: string;
  decision_entity: string;
  moisture_entity?: string;
  status_entity?: string;
  history_entity?: string;
  name?: string;
}

export interface ZoneView {
  name: string;
  moisture: number | null;
  target: number | null;
  recommendedLiters: number | null;
  availableWater: number | null;
  decision: string | null;
  decisionReason: string | null;
  wateringStatus: string | null;
  isWatering: boolean;
  canStop: boolean;
  historyCount: number;
  lastKind: string | null;
  historyEntries: Array<Record<string, unknown>>;
  greenhouse: boolean;
  protectedRain: boolean;
  temperature: number | null;
  humidity: number | null;
}

function num(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function isUnavailable(state: HassState | undefined): boolean {
  return (
    state === undefined ||
    state.state === "unavailable" ||
    state.state === "unknown"
  );
}

/**
 * Reduce the configured entity states into a single view model for rendering.
 * Missing optional entities degrade gracefully to null/empty values.
 */
export function buildZoneView(
  config: ZoneCardConfig,
  states: Record<string, HassState | undefined>,
): ZoneView {
  const decision = config.decision_entity
    ? states[config.decision_entity]
    : undefined;
  const moisture = config.moisture_entity
    ? states[config.moisture_entity]
    : undefined;
  const status = config.status_entity
    ? states[config.status_entity]
    : undefined;
  const history = config.history_entity
    ? states[config.history_entity]
    : undefined;

  const decisionAttrs = decision?.attributes ?? {};
  const statusAttrs = status?.attributes ?? {};
  const historyAttrs = history?.attributes ?? {};

  const moistureValue =
    moisture && !isUnavailable(moisture)
      ? num(moisture.state)
      : num(decisionAttrs["zone_moisture"]);

  return {
    name:
      config.name ??
      (decisionAttrs["friendly_name"] as string | undefined) ??
      "Irrigation Zone",
    moisture: moistureValue,
    target: num(decisionAttrs["target_moisture"]),
    recommendedLiters: num(decisionAttrs["recommended_liters"]),
    availableWater: num(decisionAttrs["available_water"]),
    decision: isUnavailable(decision) ? null : (decision?.state ?? null),
    decisionReason: (decisionAttrs["reason"] as string | undefined) ?? null,
    wateringStatus: isUnavailable(status) ? null : (status?.state ?? null),
    isWatering: statusAttrs["is_watering"] === true,
    canStop: statusAttrs["can_stop"] === true,
    historyCount: num(history?.state) ?? 0,
    lastKind: (historyAttrs["last_kind"] as string | undefined) ?? null,
    historyEntries: Array.isArray(historyAttrs["entries"])
      ? (historyAttrs["entries"] as Array<Record<string, unknown>>)
      : [],
    greenhouse: decisionAttrs["greenhouse"] === true,
    protectedRain: decisionAttrs["protected_rain"] === true,
    temperature: num(decisionAttrs["temperature"]),
    humidity: num(decisionAttrs["humidity"]),
  };
}

/** Run and Force Water are always offered; the engine makes the real decision. */
export function canRun(_view: ZoneView): boolean {
  return true;
}

/** Stop is offered only when the backend reports a stoppable, active run. */
export function canStop(view: ZoneView): boolean {
  return view.canStop && view.isWatering;
}

export interface OverviewCardConfig {
  type: string;
  title?: string;
  zones: ZoneCardConfig[];
}

/** Build a view model for every zone referenced by an overview card. */
export function buildOverview(
  config: OverviewCardConfig,
  states: Record<string, HassState | undefined>,
): ZoneView[] {
  const zones = Array.isArray(config.zones) ? config.zones : [];
  return zones.map((zone) => buildZoneView(zone, states));
}
