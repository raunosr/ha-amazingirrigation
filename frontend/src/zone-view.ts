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
  type?: string;
  decision_entity: string;
  moisture_entity?: string;
  status_entity?: string;
  history_entity?: string;
  name?: string;
}

/** A referenced source entity (moisture, rain, climate, safety) for display. */
export interface RelatedEntity {
  entityId: string;
  label: string;
  name: string;
  state: string | null;
  unit: string | null;
  available: boolean;
}

/** One of the two daily schedule slots, each independently toggleable. */
export interface ScheduleSlot {
  index: number;
  timeEntity: string;
  time: string | null;
  activeEntity: string;
  active: boolean;
  available: boolean;
}

/** A single learned-model parameter surfaced read-only on the card. */
export interface LearnedValue {
  key: string;
  label: string;
  entityId: string;
  value: number | null;
  unit: string | null;
  samples: number | null;
}

/** One learned water-balance parameter with explainable units/confidence. */
export interface ModelParameter {
  key: string;
  label: string;
  value: number | null;
  unit: string | null;
  confidence: number | null;
}

/** One term in the water-balance prediction, in moisture percentage points. */
export interface WaterBalanceTerm {
  key: string;
  label: string;
  value: number;
  unit: string;
}

/** Latest predictive decision explanation, normalized for display. */
export interface ModelDecisionExplanation {
  terms: WaterBalanceTerm[];
  predictedTrajectory: number[];
  horizonHours: number | null;
  predictiveReason: string | null;
  chosenLiters: number | null;
  predictedCriticalTheta: number | null;
  predictedPeakTheta: number | null;
}

/** Diagnostic model section surfaced by the Model Insight sensor. */
export interface ModelInsight {
  entityId: string;
  status: string | null;
  parameters: ModelParameter[];
  overallConfidence: number | null;
  bootstrappedDays: number | null;
  bootstrapSummary: string | null;
  modelUpdated: string | null;
  totalLiters: number | null;
  decisionExplanation: ModelDecisionExplanation | null;
}

/** A live, editable tunable backed by a native entity (number/switch). */
export interface ControlEntity {
  entityId: string;
  label: string;
  state: string | null;
  unit: string | null;
  isOn: boolean;
  available: boolean;
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
  targetMode: string | null;
  demandProfile: string | null;
  targetBandLow: number | null;
  targetBandHigh: number | null;
  references: RelatedEntity[];
  schedule: ScheduleSlot[];
  learned: LearnedValue[];
  totalVolume: number | null;
  totalVolumeUnit: string | null;
  targetControl: ControlEntity | null;
  autoTargetControl: ControlEntity | null;
  maxLitersControl: ControlEntity | null;
  enabledControl: ControlEntity | null;
  learningControl: ControlEntity | null;
  modelInsight: ModelInsight | null;
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
 * Derive the shared entity-id slug for a zone from its decision sensor.
 *
 * All of a zone's entities share Home Assistant's per-device naming, so the
 * decision sensor `sensor.<slug>_irrigation_decision` lets us locate the zone's
 * sibling entities (learned model, schedule, totals, controls) without making
 * the user wire each one into the card config.
 */
export function zoneSlug(decisionEntity: string): string {
  return decisionEntity
    .replace(/^sensor\./, "")
    .replace(/_irrigation_decision$/, "");
}

function stateOf(
  states: Record<string, HassState | undefined>,
  entityId: string,
): HassState | undefined {
  return states[entityId];
}

function unitOf(state: HassState | undefined): string | null {
  const unit = state?.attributes?.["unit_of_measurement"];
  return typeof unit === "string" ? unit : null;
}

function friendlyName(
  state: HassState | undefined,
  fallback: string,
): string {
  const name = state?.attributes?.["friendly_name"];
  return typeof name === "string" && name.length > 0 ? name : fallback;
}

function relatedEntity(
  states: Record<string, HassState | undefined>,
  entityId: string,
  label: string,
): RelatedEntity | null {
  const state = stateOf(states, entityId);
  if (!state) {
    return null;
  }
  return {
    entityId,
    label,
    name: friendlyName(state, entityId),
    state: isUnavailable(state) ? null : state.state,
    unit: unitOf(state),
    available: !isUnavailable(state),
  };
}

/** Collect the configured source sensors a zone reads, with live states. */
function buildReferences(
  refs: Record<string, unknown>,
  states: Record<string, HassState | undefined>,
): RelatedEntity[] {
  const out: RelatedEntity[] = [];
  const single: Array<[string, string]> = [
    ["forecast_rain_amount", "Rain forecast"],
    ["forecast_rain_probability", "Rain chance"],
    ["weather_forecast_entity", "Weather forecast"],
    ["observed_rain_amount", "Observed rain"],
    ["temperature_sensor", "Temperature"],
    ["humidity_sensor", "Humidity"],
    ["observed_air_temperature", "Air temperature"],
    ["observed_air_humidity", "Air humidity"],
    ["forecast_air_temperature", "Forecast air temp"],
    ["forecast_air_humidity", "Forecast air humidity"],
    ["wind_speed", "Wind speed"],
    ["solar_radiation", "Solar"],
  ];
  const moisture = Array.isArray(refs["moisture_sensors"])
    ? (refs["moisture_sensors"] as string[])
    : [];
  for (const id of moisture) {
    const entity = relatedEntity(states, id, "Moisture sensor");
    if (entity) {
      out.push(entity);
    }
  }
  for (const [key, label] of single) {
    const id = refs[key];
    if (typeof id === "string" && id) {
      const entity = relatedEntity(states, id, label);
      if (entity) {
        out.push(entity);
      }
    }
  }
  const blockers = Array.isArray(refs["safety_blockers"])
    ? (refs["safety_blockers"] as string[])
    : [];
  for (const id of blockers) {
    const entity = relatedEntity(states, id, "Safety blocker");
    if (entity) {
      out.push(entity);
    }
  }
  return out;
}

const LEARNED_DEFS: Array<{ key: string; label: string }> = [
  { key: "learned_moisture_gain_per_liter", label: "Moisture Gain per Liter" },
  { key: "learned_daily_drying_rate", label: "Daily Drying Rate" },
  { key: "learned_rain_efficiency", label: "Rain Efficiency" },
  { key: "learned_field_capacity", label: "Field Capacity" },
  { key: "learned_wilting_point", label: "Wilting Point" },
];

const MODEL_PARAMETER_DEFS: Array<{ key: string; label: string }> = [
  { key: "eta_irr", label: "Irrigation Efficiency" },
  { key: "eta_rain", label: "Rain Efficiency" },
  { key: "k_et", label: "ET Coefficient" },
  { key: "drain_rate", label: "Drainage Rate" },
  { key: "field_capacity", label: "Field Capacity" },
  { key: "wilting_point", label: "Wilting Point" },
];

const TERM_LABELS: Record<string, string> = {
  irrigation: "Irrigation added",
  rain: "Rain added",
  et: "Evapotranspiration loss",
  drainage: "Drainage loss",
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/** Build the learned-model rows for a zone from its learned sensors. */
function buildLearned(
  slug: string,
  states: Record<string, HassState | undefined>,
): LearnedValue[] {
  const out: LearnedValue[] = [];
  for (const def of LEARNED_DEFS) {
    const entityId = `sensor.${slug}_${def.key}`;
    const state = stateOf(states, entityId);
    if (!state) {
      continue;
    }
    const samples = state.attributes?.["samples"];
    out.push({
      key: def.key,
      label: def.label,
      entityId,
      value: isUnavailable(state) ? null : num(state.state),
      unit: unitOf(state),
      samples: typeof samples === "number" ? samples : null,
    });
  }
  return out;
}

function numericList(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map(num).filter((item): item is number => item !== null);
}

function buildModelParameters(
  attrs: Record<string, unknown>,
): ModelParameter[] {
  const source = asRecord(attrs["parameters"]);
  const confidence = asRecord(attrs["confidence"]);
  if (!source) {
    return [];
  }
  return MODEL_PARAMETER_DEFS.map((def) => {
    const raw = asRecord(source[def.key]);
    if (!raw) {
      return null;
    }
    return {
      key: def.key,
      label: typeof raw["name"] === "string" ? raw["name"] : def.label,
      value: num(raw["value"]),
      unit: typeof raw["unit"] === "string" ? raw["unit"] : null,
      confidence: num(raw["confidence"]) ?? num(confidence?.[def.key]),
    };
  }).filter(
    (item): item is ModelParameter =>
      item !== null && (item.value !== null || item.confidence !== null),
  );
}

function buildTerms(source: Record<string, unknown> | null): WaterBalanceTerm[] {
  const terms = asRecord(source?.["water_balance_terms"]) ?? asRecord(source?.["terms"]);
  if (!terms) {
    return [];
  }
  return Object.entries(terms)
    .map(([key, value]) => {
      const parsed = num(value);
      if (parsed === null) {
        return null;
      }
      return {
        key,
        label: TERM_LABELS[key] ?? key.replace(/_/g, " "),
        value: parsed,
        unit: "%",
      };
    })
    .filter((item): item is WaterBalanceTerm => item !== null);
}

function buildDecisionExplanation(
  insightAttrs: Record<string, unknown>,
  decisionAttrs: Record<string, unknown>,
): ModelDecisionExplanation | null {
  const explanation =
    asRecord(insightAttrs["decision_explanation"]) ??
    asRecord(decisionAttrs["explanation"]);
  const termSource = { ...(explanation ?? {}), ...insightAttrs };
  const terms = buildTerms(termSource);
  const predictedTrajectory =
    numericList(insightAttrs["predicted_trajectory"]).length > 0
      ? numericList(insightAttrs["predicted_trajectory"])
      : numericList(decisionAttrs["predicted_trajectory"]).length > 0
        ? numericList(decisionAttrs["predicted_trajectory"])
        : numericList(explanation?.["predicted_trajectory"]);
  const horizonHours =
    num(insightAttrs["horizon_hours"]) ??
    num(decisionAttrs["horizon_hours"]) ??
    num(explanation?.["horizon_hours"]);
  const chosenLiters =
    num(insightAttrs["chosen_liters"]) ??
    num(explanation?.["chosen_liters"]) ??
    num(decisionAttrs["recommended_liters"]);
  const predictedCriticalTheta =
    num(insightAttrs["predicted_critical_theta"]) ??
    num(explanation?.["predicted_critical_theta_with_water"]) ??
    num(explanation?.["predicted_critical_theta_without_water"]);
  const predictedPeakTheta =
    num(insightAttrs["predicted_peak_theta"]) ??
    num(explanation?.["predicted_peak_theta"]);
  if (
    !terms.length &&
    !predictedTrajectory.length &&
    horizonHours === null &&
    chosenLiters === null
  ) {
    return null;
  }
  return {
    terms,
    predictedTrajectory,
    horizonHours,
    predictiveReason: (decisionAttrs["reason"] as string | undefined) ?? null,
    chosenLiters,
    predictedCriticalTheta,
    predictedPeakTheta,
  };
}

function buildModelInsight(
  slug: string,
  states: Record<string, HassState | undefined>,
  decisionAttrs: Record<string, unknown>,
): ModelInsight | null {
  const entityId = `sensor.${slug}_model_insight`;
  const state = stateOf(states, entityId);
  const attrs = state?.attributes ?? {};
  const parameters = buildModelParameters(attrs);
  const decisionExplanation = buildDecisionExplanation(attrs, decisionAttrs);
  const bootstrappedDays = num(attrs["bootstrapped_days"]);
  const bootstrapSummary =
    typeof attrs["bootstrap_summary"] === "string"
      ? attrs["bootstrap_summary"]
      : null;
  if (
    !parameters.length &&
    decisionExplanation === null &&
    bootstrappedDays === null
  ) {
    return null;
  }
  return {
    entityId,
    status: isUnavailable(state) ? null : (state?.state ?? null),
    parameters,
    overallConfidence: num(attrs["overall_confidence"]),
    bootstrappedDays,
    bootstrapSummary,
    modelUpdated:
      typeof attrs["model_updated"] === "string" ? attrs["model_updated"] : null,
    totalLiters: num(attrs["total_liters"]),
    decisionExplanation,
  };
}

/** Build the two schedule slots from their native time + switch entities. */
function buildSchedule(
  slug: string,
  states: Record<string, HassState | undefined>,
): ScheduleSlot[] {
  const out: ScheduleSlot[] = [];
  for (const index of [1, 2]) {
    const timeEntity = `time.${slug}_schedule_${index}_time`;
    const activeEntity = `switch.${slug}_schedule_${index}_active`;
    const timeState = stateOf(states, timeEntity);
    const activeState = stateOf(states, activeEntity);
    if (!timeState && !activeState) {
      continue;
    }
    const raw = timeState && !isUnavailable(timeState) ? timeState.state : null;
    out.push({
      index,
      timeEntity,
      time: raw ? raw.slice(0, 5) : null,
      activeEntity,
      active: activeState?.state === "on",
      available: !isUnavailable(timeState),
    });
  }
  return out;
}

function controlEntity(
  states: Record<string, HassState | undefined>,
  entityId: string,
  label: string,
): ControlEntity | null {
  const state = stateOf(states, entityId);
  if (!state) {
    return null;
  }
  return {
    entityId,
    label,
    state: isUnavailable(state) ? null : state.state,
    unit: unitOf(state),
    isOn: state.state === "on",
    available: !isUnavailable(state),
  };
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

  const slug = zoneSlug(config.decision_entity);
  const refs =
    (decisionAttrs["references"] as Record<string, unknown> | undefined) ?? {};
  const totalVolumeState = stateOf(
    states,
    `sensor.${slug}_total_watering_volume`,
  );

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
    targetMode:
      typeof decisionAttrs["target_mode"] === "string"
        ? (decisionAttrs["target_mode"] as string)
        : null,
    demandProfile:
      typeof decisionAttrs["demand_profile"] === "string"
        ? (decisionAttrs["demand_profile"] as string)
        : null,
    targetBandLow: num(decisionAttrs["target_band_low"]),
    targetBandHigh: num(decisionAttrs["target_band_high"]),
    references: buildReferences(refs, states),
    schedule: buildSchedule(slug, states),
    learned: buildLearned(slug, states),
    totalVolume:
      totalVolumeState && !isUnavailable(totalVolumeState)
        ? num(totalVolumeState.state)
        : null,
    totalVolumeUnit: unitOf(totalVolumeState),
    targetControl: controlEntity(
      states,
      `number.${slug}_target_moisture`,
      "Target Moisture",
    ),
    autoTargetControl: controlEntity(
      states,
      `switch.${slug}_target_automatic`,
      "Automatic Target",
    ),
    maxLitersControl: controlEntity(
      states,
      `number.${slug}_max_liters_per_run`,
      "Max Liters per Run",
    ),
    enabledControl: controlEntity(
      states,
      `switch.${slug}_zone_enabled`,
      "Zone Enabled",
    ),
    learningControl: controlEntity(
      states,
      `switch.${slug}_learning_enabled`,
      "Learning Enabled",
    ),
    modelInsight: buildModelInsight(slug, states, decisionAttrs),
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

/**
 * Return the integration's per-zone decision sensors, used to pre-fill the
 * visual editors and card stub configs so the picker preview renders.
 */
export function decisionEntities(
  states: Record<string, HassState | undefined> | undefined,
): string[] {
  if (!states) {
    return [];
  }
  return Object.keys(states)
    .filter(
      (id) => id.startsWith("sensor.") && id.endsWith("_irrigation_decision"),
    )
    .sort();
}
