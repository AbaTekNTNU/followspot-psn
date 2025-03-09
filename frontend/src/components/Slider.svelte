<script lang="ts">
  import type { TrackerData } from "$lib/utils/types";
  import Modal from "./Modal.svelte";

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

  let arena_state: "full_arena" | "scene_only" = $state("scene_only");

  let tracker = $state<TrackerData | undefined>(undefined);

  $effect(() => {
    tracker = trackers.find((ball) => ball.id === selected);
  });

  const onchange = () => {
    const x_send = tracker!.x / width;
    const y_send = tracker!.y / height;
    ws?.send(
      JSON.stringify({
        id: tracker!.id,
        x: x_send,
        y: y_send,
        z: tracker!.z,
      }),
    );
  };

  type arenaResponse = {
    mode: "full_arena" | "scene_only";
  };

  const buttonAction = async () => {
    await fetch("/mode")
      .then((res) => res.json())
      .then((data: arenaResponse) => {
        arena_state = data.mode;
      });

    await fetch("/mode", {
      method: "POST",
      body: JSON.stringify({
        mode: arena_state === "full_arena" ? "scene_only" : "full_arena",
      }),
    });
  };

  let z_viz = $derived(tracker?.z.toFixed(2));
</script>

<div class="slider-container ml-auto w-20">
  <Modal action={buttonAction} />
  {#if tracker}
    <input
      type="range"
      id="z"
      min="0"
      max="4"
      step="0.01"
      oninput={onchange}
      bind:value={tracker.z}
    />
    <output for="z">{z_viz} m</output>
  {/if}
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
    width: 120px;
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
