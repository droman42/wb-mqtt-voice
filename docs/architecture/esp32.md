# ESP32 voice satellite — MOVED

The ESP32 voice satellite is its own product now, with its own repo — the narrative
architecture story, the hardware/firmware design, and the fleet-provisioning plane all live in
[**locveil-satellite**](https://github.com/locveil/locveil-satellite) (this page:
[`docs/architecture/esp32.md`](https://github.com/locveil/locveil-satellite/blob/main/docs/architecture/esp32.md)).

What stays in this repo is Irene's half of the pair: the WebSocket endpoints a satellite talks
to (frame-by-frame reference: the [WebSocket API guide](../guides/websocket-api.md)), the client
registry, and the [Python desktop satellite](../guides/satellite.md).
