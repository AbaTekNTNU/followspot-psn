<script lang="ts">
  import { onMount } from "svelte";
  import type { TrackerData } from "../utils/types";
  import Drag from "./Drag.svelte";

  let ws: WebSocket | null = $state(null);
  let image: HTMLImageElement | null = $state(null);

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

<div class="relative">
  <img src="/bg.png" alt="" bind:this={image} class="scale-50" />
  <div
    bind:this={parent}
    class="absolute inset-0 border border-red-500"
    style={"width: " +
      image?.getBoundingClientRect().width +
      "px; height: " +
      image?.getBoundingClientRect().height +
      "px;" +
      "transform: translate(50%, 50%);"}
  >
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
</div>
