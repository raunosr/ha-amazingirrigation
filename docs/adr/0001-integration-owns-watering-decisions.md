# Integration owns watering decisions

Amazing Irrigation will own the skip, reduce, and water decision for each Irrigation Zone, while schedules only create Run Requests. Schedules may be simple schedules built into the integration or external Home Assistant automations, but neither owns the watering decision. This avoids duplicating per-zone decision branches across Home Assistant automations and keeps every decision explainable through the integration's zone state.
