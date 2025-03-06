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

  let z_viz = $derived((trackers[selected].z).toFixed(2))
</script>

<div class="slider-container">
  <input
    type="range"
    id="z"
    min="0"
    max="4"
    step="0.01"
    oninput="{onchange}"
    bind:value={trackers[selected].z}
  />
  <output for="z">{z_viz} m</output>
</div>

<style>
  .slider-container {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  input {
    writing-mode: vertical-lr;
    direction: rtl;
    appearance: none;
    width: 75px;
    height: 50%;
    vertical-align: bottom;
  }


    /* WebKit Browsers (Chrome, Safari, Edge) */
  input::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 50px; /* Larger size */
    height: 50px;
    background: red; /* Customize color */
    margin-left: -22px; /* Center the thumb */
    border-radius: 50%;
    cursor: pointer;
  }

  input::-webkit-slider-runnable-track {
    background: lightgray; /* Customize track */
    width: 6px;
    border-radius: 3px;
  }

</style>
