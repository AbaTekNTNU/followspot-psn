<script lang="ts">
  import { onMount } from "svelte";
  import type { TrackerData } from "../utils/types";
  import Drag from "./Drag.svelte";

  let ws: WebSocket | null = $state(null);

  let parent: HTMLElement | null = $state(null);

  let trackers: TrackerData[] = $state([
    { id: 1, x: 0, y: 0 },
    { id: 2, x: 0, y: 0 },
  ]);

  onMount(() => {
    ws = new WebSocket("/ws");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      trackers = data;
    };
  });
</script>

<div bind:this={parent} class="relative border border-red-500">
  <img src="/scene_drawing.png" alt="moradi" class="absolute" />
  {#each trackers as tracker}
    <Drag
      bind:id={tracker.id}
      bind:x={tracker.x}
      bind:y={tracker.y}
      {ws}
      {parent}
    />
  {/each}
</div>
