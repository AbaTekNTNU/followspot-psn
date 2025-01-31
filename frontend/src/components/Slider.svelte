<script lang="ts">
  import type { TrackerData } from "$lib/utils/types";

  type Props = {
    selected: number;
    trackers: TrackerData[];
    ws: WebSocket | null;
    width: number;
    height: number;
  };

  let {
    selected = $bindable(),
    trackers = $bindable(),
    ws,
    width = $bindable(),
    height = $bindable(),
  }: Props = $props();

  const onchange = () => {
    const x_send = trackers[selected].x / width;
    const y_send = trackers[selected].y / height;
    ws?.send(
      JSON.stringify({
        id: trackers[selected].id,
        x: x_send,
        y: y_send,
        z: trackers[selected].z,
      }),
    );
  };

  let z_viz = $derived((trackers[selected].z * 2).toFixed(2))
</script>

<div>
  <label for="z">Z</label>
  <input
    type="range"
    id="z"
    min="0"
    max="1"
    step="0.01"
    oninput="{onchange}"
    bind:value={trackers[selected].z}
  />
  <output for="z">{z_viz} m</output>
</div>

<style>
  input {
    writing-mode: vertical-lr;
    direction: rtl;
    appearance: slider-vertical;
    width: 26px;
    height: 50%;
    vertical-align: bottom;
  }
</style>
