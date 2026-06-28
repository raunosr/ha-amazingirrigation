# Physics-informed water-balance learning and predictive control

Amazing Irrigation will model each Irrigation Zone with a physics-informed **Soil Water Balance** rather than independent moving-average estimators. Zone Moisture is advanced over discrete intervals by

```
theta_next = theta + Irrigation Efficiency · liters
                   + Rain Efficiency · rain_mm
                   − Evapotranspiration(climate, dt)
                   − Drainage(theta, Field Capacity)
```

Because this balance is linear in its coefficients (Irrigation Efficiency, Rain Efficiency, an evapotranspiration coefficient and a drainage rate), every observed interval becomes one regression row. A recursive joint estimator (Kalman/RLS with covariance) learns all coefficients together with a confidence per coefficient (**Model Confidence**), instead of the previous EMA branches that could only attribute one effect per observation. Field Capacity and Wilting Point continue to track a bounded moisture envelope. Manual values always override learned ones, and every coefficient stays inside safe bounds — preserving the existing safety and override guarantees.

To learn fast, a **History Bootstrap** replays each zone's recorder history (moisture, rain and climate, with irrigation events taken from recorded Watering Events or inferred from unexplained moisture rises) through the same estimator at setup, and on demand via the `amazing_irrigation.relearn_from_history` service and a per-zone "Re-learn from History" button. It degrades gracefully when recorder history is unavailable and reports how much history it used.

The controller becomes **Predictive Control**: given the learned model, the current Zone Moisture and a forecast horizon to the next active schedule slot, it simulates the future trajectory and applies only the minimum liters needed to keep predicted moisture inside the configurable **Target Range** without exceeding Field Capacity — minimizing overwatering, drainage losses and unnecessary runs. When the model or forecast is unavailable it falls back to the existing rule-based decision.

Every conclusion is reviewable on the device page: a **Model Insight** diagnostic sensor and the zone card surface the learned parameters with their confidence, the History Bootstrap summary, and the water-balance breakdown, predicted trajectory and chosen liters behind each Irrigation Decision.

This decision changes *how* liters are decided and learned, not *who* decides. The integration still owns the watering decision (ADR&nbsp;0001) and remains the zone source of truth (ADR&nbsp;0002); schedules still only create Run Requests, and the Zone State stays the live source of truth that every Irrigation Decision reads.
