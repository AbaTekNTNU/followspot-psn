<script lang="ts">
  import { onMount } from "svelte";
  import type { TrackerData } from "../utils/types";
  import Drag from "./Drag.svelte";

  let ws: WebSocket | null = $state(null);
  let image: HTMLImageElement | null = $state(null);

  let trackers: TrackerData[] = $state([
    { id: 1, x: 0, y: 0 },
    { id: 2, x: 0, y: 0 },
  ]);

  let width = $state(0);
  let height = $state(0);

  const resize = () => {
    width = image?.getBoundingClientRect().width ?? 0;
    height = image?.getBoundingClientRect().height ?? 0;
  };

  onMount(() => {
    ws = new WebSocket("/ws");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      for (const tracker of data) {
        tracker.x *= width
        tracker.y *= height
        }
      trackers = data;
    };

    width = image?.getBoundingClientRect().width ?? 0;
    height = image?.getBoundingClientRect().height ?? 0;
  });
</script>

<svelte:window onresize={resize} />
<div class="relative">
  <img
    src="/scene_drawing.png"
    alt=""
    bind:this={image}
    class="max-w-screen max-h-screen"
    onload={resize}
  />
  <div class="absolute inset-0 border border-red-500">
    {#each trackers as tracker}
      <Drag
        bind:id={tracker.id}
        bind:x={tracker.x}
        bind:y={tracker.y}
        bind:width
        bind:height
        {ws}
      />
    {/each}
  </div>
</div>
