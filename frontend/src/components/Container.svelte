<script lang="ts">
  import { onMount } from "svelte";
  import type { TrackerData } from "../utils/types";
  import Drag from "./Drag.svelte";
  import Slider from "./Slider.svelte";

  let ws: WebSocket | null = $state(null);
  let image: HTMLImageElement | null = $state(null);

  let trackers: TrackerData[] = $state([
    { id: 1, x: 0, y: 0, z: 0 },
    { id: 2, x: 0, y: 0, z: 0 },
  ]);

  let width = $state(0);
  let height = $state(0);
  let selected = $state(0);

  let debounce: number | null = $state(null);

  const connect = () => {
    if (ws) {
      ws.close();
    }

    ws = new WebSocket("/ws");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(data)

      if (data.refresh && image) {
          image.src = `/background_image?${Math.random()}`;
        return;
      }

      else {
        for (const tracker of data) {
          tracker.x *= width;
          tracker.y *= height;
        }
        trackers = data;
      }
    };
  };

  const resize = () => {
    width = image?.getBoundingClientRect().width ?? 0;
    height = image?.getBoundingClientRect().height ?? 0;

    if (debounce) {
      clearTimeout(debounce);
    }

    debounce = setTimeout(() => {
      connect();
    }, 200);
  };

  onMount(() => {
    connect();

    width = image?.getBoundingClientRect().width ?? 0;
    height = image?.getBoundingClientRect().height ?? 0;
  });


</script>

<svelte:window onresize={resize} />
<div class="flex h-screen items-center justify-center w-screen">
  <div class="w-20 mr-auto"></div>
  <div class="relative">
    <img
      src="/background_image?342038402"
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
          bind:z={tracker.z}
          bind:width
          bind:height
          bind:selected
          {ws}
        />
      {/each}
    </div>
  </div>

  <Slider bind:trackers {ws} bind:height bind:width bind:selected />
</div>
