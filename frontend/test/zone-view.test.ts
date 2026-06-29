import { describe, it, expect } from "vitest";

import {
  buildOverview,
  buildZoneView,
  canRun,
  canStop,
  decisionEntities,
  zoneSlug,
  type HassState,
  type OverviewCardConfig,
  type ZoneCardConfig,
} from "../src/zone-view";

const config: ZoneCardConfig = {
  type: "custom:amazing-irrigation-card",
  decision_entity: "sensor.herb_decision",
  moisture_entity: "sensor.herb_moisture",
  status_entity: "sensor.herb_status",
  history_entity: "sensor.herb_history",
  name: "Herb Bed",
};

function states(
  overrides: Record<string, HassState> = {},
): Record<string, HassState> {
  return {
    "sensor.herb_moisture": { state: "32.5", attributes: {} },
    "sensor.herb_decision": {
      state: "water",
      attributes: {
        reason: "below_target",
        recommended_liters: 12.5,
        target_moisture: 40,
        available_water: 0.5,
      },
    },
    "sensor.herb_status": {
      state: "confirmed",
      attributes: { is_watering: true, can_stop: true },
    },
    "sensor.herb_history": {
      state: "3",
      attributes: {
        last_kind: "watering_event",
        entries: [
          { kind: "watering_event", status: "confirmed", measured_liters: 8 },
          { kind: "decision", action: "water", reason: "below_target" },
        ],
      },
    },
    ...overrides,
  };
}

describe("decisionEntities", () => {
  it("returns sorted irrigation decision sensors only", () => {
    const result = decisionEntities({
      "sensor.zone_b_irrigation_decision": { state: "water", attributes: {} },
      "sensor.zone_a_irrigation_decision": { state: "skip", attributes: {} },
      "sensor.zone_a_status": { state: "idle", attributes: {} },
      "binary_sensor.zone_a_irrigation_decision": { state: "on", attributes: {} },
    });
    expect(result).toEqual([
      "sensor.zone_a_irrigation_decision",
      "sensor.zone_b_irrigation_decision",
    ]);
  });

  it("returns an empty list when states are missing", () => {
    expect(decisionEntities(undefined)).toEqual([]);
  });
});

describe("buildZoneView", () => {
  it("maps entity states into a single view model", () => {
    const view = buildZoneView(config, states());
    expect(view.name).toBe("Herb Bed");
    expect(view.moisture).toBe(32.5);
    expect(view.target).toBe(40);
    expect(view.recommendedLiters).toBe(12.5);
    expect(view.availableWater).toBe(0.5);
    expect(view.decision).toBe("water");
    expect(view.decisionReason).toBe("below_target");
    expect(view.wateringStatus).toBe("confirmed");
    expect(view.isWatering).toBe(true);
    expect(view.canStop).toBe(true);
    expect(view.historyCount).toBe(3);
    expect(view.lastKind).toBe("watering_event");
    expect(view.historyEntries).toHaveLength(2);
  });

  it("degrades gracefully when optional entities are missing", () => {
    const view = buildZoneView(
      { type: "x", decision_entity: "sensor.herb_decision" },
      { "sensor.herb_decision": { state: "skip", attributes: {} } },
    );
    expect(view.moisture).toBeNull();
    expect(view.target).toBeNull();
    expect(view.recommendedLiters).toBeNull();
    expect(view.availableWater).toBeNull();
    expect(view.isWatering).toBe(false);
    expect(view.canStop).toBe(false);
    expect(view.historyEntries).toEqual([]);
    expect(view.modelInsight).toBeNull();
  });

  it("treats unavailable decision state as no decision", () => {
    const view = buildZoneView(
      config,
      states({
        "sensor.herb_decision": { state: "unavailable", attributes: {} },
      }),
    );
    expect(view.decision).toBeNull();
  });
});

describe("greenhouse context", () => {
  it("exposes greenhouse, protected-rain, temperature and humidity", () => {
    const view = buildZoneView(
      config,
      states({
        "sensor.herb_decision": {
          state: "water",
          attributes: {
            reason: "below_target",
            greenhouse: true,
            protected_rain: true,
            temperature: 27.4,
            humidity: 65,
          },
        },
      }),
    );
    expect(view.greenhouse).toBe(true);
    expect(view.protectedRain).toBe(true);
    expect(view.temperature).toBe(27.4);
    expect(view.humidity).toBe(65);
  });

  it("defaults greenhouse fields off for normal zones", () => {
    const view = buildZoneView(config, states());
    expect(view.greenhouse).toBe(false);
    expect(view.protectedRain).toBe(false);
    expect(view.temperature).toBeNull();
    expect(view.humidity).toBeNull();
  });
});

describe("demand profile + target band", () => {
  it("exposes target mode, demand profile and the derived band", () => {
    const view = buildZoneView(
      config,
      states({
        "sensor.herb_decision": {
          state: "skip",
          attributes: {
            target_mode: "auto",
            demand_profile: "high",
            target_band_low: 36,
            target_band_high: 42,
          },
        },
      }),
    );
    expect(view.targetMode).toBe("auto");
    expect(view.demandProfile).toBe("high");
    expect(view.targetBandLow).toBe(36);
    expect(view.targetBandHigh).toBe(42);
  });

  it("leaves profile/band null when not provided", () => {
    const view = buildZoneView(config, states());
    expect(view.targetMode).toBeNull();
    expect(view.demandProfile).toBeNull();
    expect(view.targetBandLow).toBeNull();
    expect(view.targetBandHigh).toBeNull();
  });
});

describe("buildOverview", () => {
  it("builds a view model per configured zone", () => {
    const overview: OverviewCardConfig = {
      type: "custom:amazing-irrigation-overview-card",
      title: "Garden",
      zones: [
        config,
        {
          type: "x",
          decision_entity: "sensor.green_decision",
          name: "Greenhouse",
        },
      ],
    };
    const all = states({
      "sensor.green_decision": {
        state: "skip",
        attributes: { greenhouse: true, protected_rain: true },
      },
    });
    const views = buildOverview(overview, all);
    expect(views).toHaveLength(2);
    expect(views[0].name).toBe("Herb Bed");
    expect(views[1].name).toBe("Greenhouse");
    expect(views[1].greenhouse).toBe(true);
    expect(views[1].decision).toBe("skip");
  });

  it("returns an empty list when no zones are configured", () => {
    expect(
      buildOverview({ type: "x", zones: [] } as OverviewCardConfig, {}),
    ).toEqual([]);
  });
});

describe("capability gating", () => {
  it("always allows Run", () => {
    expect(canRun(buildZoneView(config, states()))).toBe(true);
  });

  it("allows Stop only when watering and the backend permits it", () => {
    expect(canStop(buildZoneView(config, states()))).toBe(true);

    const notWatering = buildZoneView(
      config,
      states({
        "sensor.herb_status": {
          state: "idle",
          attributes: { is_watering: false, can_stop: true },
        },
      }),
    );
    expect(canStop(notWatering)).toBe(false);

    const noStopPath = buildZoneView(
      config,
      states({
        "sensor.herb_status": {
          state: "confirmed",
          attributes: { is_watering: true, can_stop: false },
        },
      }),
    );
    expect(canStop(noStopPath)).toBe(false);
  });
});

describe("zoneSlug", () => {
  it("strips the decision sensor prefix and suffix", () => {
    expect(zoneSlug("sensor.herb_bed_irrigation_decision")).toBe("herb_bed");
  });

  it("leaves a non-standard entity id usable as a base", () => {
    expect(zoneSlug("sensor.herb_decision")).toBe("herb_decision");
  });
});

describe("surfaced zone entities", () => {
  const slug = "herb_bed";
  const decisionEntity = `sensor.${slug}_irrigation_decision`;
  const cfg: ZoneCardConfig = { type: "x", decision_entity: decisionEntity };

  function fullStates(): Record<string, HassState> {
    return {
      [decisionEntity]: {
        state: "water",
        attributes: {
          reason: "below_target",
          references: {
            moisture_sensors: ["sensor.soil_a", "sensor.soil_b"],
            weather_forecast_entity: "weather.forecast_home",
            observed_rain_amount: "sensor.rain_today",
            temperature_sensor: "sensor.gh_temp",
            observed_air_temperature: "sensor.air_temp",
            observed_air_humidity: "sensor.air_humidity",
            forecast_air_temperature: "sensor.forecast_temp",
            forecast_air_humidity: "sensor.forecast_humidity",
            wind_speed: "sensor.wind_speed",
            solar_radiation: "sensor.solar_radiation",
            safety_blockers: ["binary_sensor.valve_fault"],
          },
        },
      },
      "sensor.soil_a": {
        state: "30",
        attributes: { unit_of_measurement: "%", friendly_name: "Soil A" },
      },
      "sensor.soil_b": { state: "34", attributes: { unit_of_measurement: "%" } },
      "weather.forecast_home": {
        state: "cloudy",
        attributes: { friendly_name: "Home forecast" },
      },
      "sensor.rain_today": {
        state: "2.4",
        attributes: { unit_of_measurement: "mm" },
      },
      "sensor.gh_temp": {
        state: "21",
        attributes: { unit_of_measurement: "°C" },
      },
      "sensor.air_temp": {
        state: "22",
        attributes: { unit_of_measurement: "°C" },
      },
      "sensor.air_humidity": {
        state: "61",
        attributes: { unit_of_measurement: "%" },
      },
      "sensor.forecast_temp": {
        state: "24",
        attributes: { unit_of_measurement: "°C" },
      },
      "sensor.forecast_humidity": {
        state: "58",
        attributes: { unit_of_measurement: "%" },
      },
      "sensor.wind_speed": {
        state: "3.5",
        attributes: { unit_of_measurement: "m/s" },
      },
      "sensor.solar_radiation": {
        state: "430",
        attributes: { unit_of_measurement: "W/m²" },
      },
      "binary_sensor.valve_fault": { state: "off", attributes: {} },
      [`sensor.${slug}_total_watering_volume`]: {
        state: "123.4",
        attributes: { unit_of_measurement: "L" },
      },
      [`sensor.${slug}_learned_moisture_gain_per_liter`]: {
        state: "1.8",
        attributes: { unit_of_measurement: "%/L", samples: 5 },
      },
      [`sensor.${slug}_learned_field_capacity`]: {
        state: "unknown",
        attributes: {},
      },
      [`sensor.${slug}_model_insight`]: {
        state: "65% confidence",
        attributes: {
          parameters: {
            eta_irr: {
              name: "Irrigation Efficiency",
              value: 1.5,
              unit: "%/L",
              confidence: 0.8,
            },
            eta_rain: {
              name: "Rain Efficiency",
              value: 0.9,
              unit: "%/mm",
              confidence: 0.6,
            },
            k_et: {
              name: "ET Coefficient",
              value: 0.65,
              unit: null,
              confidence: 0.7,
            },
            drain_rate: {
              name: "Drainage Rate",
              value: 0.14,
              unit: "1/h",
              confidence: 0.5,
            },
          },
          confidence: {
            eta_irr: 0.8,
            eta_rain: 0.6,
            k_et: 0.7,
            drain_rate: 0.5,
          },
          overall_confidence: 0.65,
          bootstrapped_days: 12,
          bootstrap_summary: "Learned from 12 days of history",
          water_balance_terms: {
            irrigation: 3,
            rain: 1.2,
            et: -0.8,
            drainage: -0.1,
          },
          predicted_trajectory: [39.2, 40.1, 40.4],
          horizon_hours: 3,
          chosen_liters: 2,
          predicted_critical_theta: 39.2,
          predicted_peak_theta: 40.4,
          decision_explanation: {
            terms: { irrigation: 3, rain: 1.2, et: -0.8, drainage: -0.1 },
            predicted_trajectory: [39.2, 40.1, 40.4],
            horizon_hours: 3,
            chosen_liters: 2,
          },
          model_updated: "2026-06-28T12:00:00+00:00",
          total_liters: 123.4,
        },
      },
      [`time.${slug}_schedule_1_time`]: {
        state: "21:00:00",
        attributes: {},
      },
      [`switch.${slug}_schedule_1_active`]: { state: "on", attributes: {} },
      [`time.${slug}_schedule_2_time`]: { state: "06:30:00", attributes: {} },
      [`switch.${slug}_schedule_2_active`]: { state: "off", attributes: {} },
      [`number.${slug}_target_moisture`]: {
        state: "40",
        attributes: { unit_of_measurement: "%" },
      },
      [`number.${slug}_max_liters_per_run`]: {
        state: "15",
        attributes: { unit_of_measurement: "L" },
      },
      [`switch.${slug}_zone_enabled`]: { state: "on", attributes: {} },
      [`switch.${slug}_learning_enabled`]: { state: "off", attributes: {} },
    };
  }

  it("lists referenced source sensors with live states", () => {
    const view = buildZoneView(cfg, fullStates());
    expect(view.references.map((r) => r.entityId)).toEqual([
      "sensor.soil_a",
      "sensor.soil_b",
      "weather.forecast_home",
      "sensor.rain_today",
      "sensor.gh_temp",
      "sensor.air_temp",
      "sensor.air_humidity",
      "sensor.forecast_temp",
      "sensor.forecast_humidity",
      "sensor.wind_speed",
      "sensor.solar_radiation",
      "binary_sensor.valve_fault",
    ]);
    expect(view.references[0].name).toBe("Soil A");
    expect(view.references[0].label).toBe("Moisture sensor");
    expect(view.references[2].label).toBe("Weather forecast");
    expect(view.references[3].label).toBe("Observed rain");
    expect(view.references[5].label).toBe("Air temperature");
    expect(view.references[6].label).toBe("Air humidity");
    expect(view.references[7].label).toBe("Forecast air temp");
    expect(view.references[8].label).toBe("Forecast air humidity");
    expect(view.references[9].label).toBe("Wind speed");
    expect(view.references[10].label).toBe("Solar");
    expect(view.references[11].label).toBe("Safety blocker");
  });

  it("skips references whose entity is missing", () => {
    const s = fullStates();
    delete s["sensor.soil_b"];
    const view = buildZoneView(cfg, s);
    expect(view.references.map((r) => r.entityId)).not.toContain(
      "sensor.soil_b",
    );
  });

  it("builds the two schedule slots from time and switch entities", () => {
    const view = buildZoneView(cfg, fullStates());
    expect(view.schedule).toHaveLength(2);
    expect(view.schedule[0]).toMatchObject({
      index: 1,
      time: "21:00",
      active: true,
    });
    expect(view.schedule[1]).toMatchObject({
      index: 2,
      time: "06:30",
      active: false,
    });
  });

  it("surfaces learned values, treating unknown as not-yet-learned", () => {
    const view = buildZoneView(cfg, fullStates());
    const gain = view.learned.find(
      (l) => l.key === "learned_moisture_gain_per_liter",
    );
    expect(gain).toMatchObject({ value: 1.8, unit: "%/L", samples: 5 });
    const fc = view.learned.find((l) => l.key === "learned_field_capacity");
    expect(fc?.value).toBeNull();
  });

  it("exposes total volume and editable controls", () => {
    const view = buildZoneView(cfg, fullStates());
    expect(view.totalVolume).toBe(123.4);
    expect(view.totalVolumeUnit).toBe("L");
    expect(view.targetControl?.state).toBe("40");
    expect(view.maxLitersControl?.state).toBe("15");
    expect(view.enabledControl?.isOn).toBe(true);
    expect(view.learningControl?.isOn).toBe(false);
  });

  it("builds model insight from the diagnostic sensor", () => {
    const view = buildZoneView(cfg, fullStates());
    expect(view.modelInsight?.status).toBe("65% confidence");
    expect(view.modelInsight?.overallConfidence).toBe(0.65);
    expect(view.modelInsight?.bootstrappedDays).toBe(12);
    expect(view.modelInsight?.bootstrapSummary).toBe(
      "Learned from 12 days of history",
    );
    expect(view.modelInsight?.parameters[0]).toMatchObject({
      key: "eta_irr",
      label: "Irrigation Efficiency",
      value: 1.5,
      unit: "%/L",
      confidence: 0.8,
    });
    expect(view.modelInsight?.decisionExplanation?.predictedTrajectory).toEqual([
      39.2, 40.1, 40.4,
    ]);
    expect(view.modelInsight?.decisionExplanation?.horizonHours).toBe(3);
    expect(view.modelInsight?.decisionExplanation?.chosenLiters).toBe(2);
    expect(view.modelInsight?.decisionExplanation?.terms).toContainEqual({
      key: "irrigation",
      label: "Irrigation added",
      value: 3,
      unit: "%",
    });
    expect(view.modelInsight?.decisionExplanation?.predictedCriticalTheta).toBe(
      39.2,
    );
  });

  it("degrades to empty surfaces when no sibling entities exist", () => {
    const view = buildZoneView(cfg, {
      [decisionEntity]: { state: "skip", attributes: {} },
    });
    expect(view.references).toEqual([]);
    expect(view.schedule).toEqual([]);
    expect(view.learned).toEqual([]);
    expect(view.modelInsight).toBeNull();
    expect(view.totalVolume).toBeNull();
    expect(view.targetControl).toBeNull();
  });
});
