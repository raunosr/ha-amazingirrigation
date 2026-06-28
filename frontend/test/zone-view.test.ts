import { describe, it, expect } from "vitest";

import {
  buildZoneView,
  canRun,
  canStop,
  type HassState,
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
