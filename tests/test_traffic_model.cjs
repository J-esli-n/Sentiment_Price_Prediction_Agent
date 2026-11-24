const test = require("node:test");
const assert = require("node:assert/strict");
const { findFastestRoute, predictCongestion } = require("../simulation/traffic-model.js");

const junctions = ["A", "B", "C", "E", "F"];
const roads = [
  { from: "A", to: "B", distanceKm: 2, congestion: 10 },
  { from: "B", to: "C", distanceKm: 7, congestion: 90 },
  { from: "B", to: "E", distanceKm: 2, congestion: 10 },
  { from: "E", to: "F", distanceKm: 2, congestion: 10 },
  { from: "F", to: "C", distanceKm: 2, congestion: 10 },
];

test("Dijkstra selects the less congested fastest route rather than the direct road", () => {
  const result = findFastestRoute("A", "C", junctions, roads);
  assert.deepEqual(result.nodes, ["A", "B", "E", "F", "C"]);
  assert.ok(result.travelMinutes > 0);
});

test("Dijkstra reports disconnected destinations", () => {
  assert.throws(() => findFastestRoute("A", "Z", junctions, roads), RangeError);
});

test("congestion forecast is bounded and responds to incoming traffic", () => {
  const quiet = predictCongestion({ currentPercent: 40, vehicleCount: 20, incomingPerMinute: 2 });
  const busy = predictCongestion({ currentPercent: 40, vehicleCount: 20, incomingPerMinute: 15 });
  assert.ok(busy > quiet);
  assert.equal(predictCongestion({ currentPercent: 98, vehicleCount: 0, incomingPerMinute: 50 }), 100);
});
