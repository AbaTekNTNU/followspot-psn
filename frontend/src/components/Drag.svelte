<script lang="ts">
  type Props = {
    id: number;
    x: number;
    y: number;
    width: number;
    height: number;
    ws: WebSocket | null;
  };

  let {
    id = $bindable(),
    x = $bindable(),
    y = $bindable(),
    ws = $bindable(),
    width = $bindable(),
    height = $bindable(),
  }: Props = $props();

  let element: HTMLElement;

  let vis_x = $state(0);

  let vis_y = $state(0);

  $effect(() => {
    vis_x = x + width / 2 - (element.clientWidth ?? 0) / 2;

    vis_y = y + height / 2 - (element.clientHeight ?? 0) / 2;
  });

  let capturedPointerId: number | null = $state(null);

  function onPointerDown(e: PointerEvent) {
    element!.setPointerCapture(e.pointerId);
    capturedPointerId = e.pointerId;
  }
  function onPointerUp(e: PointerEvent) {
    capturedPointerId = null;
    element!.releasePointerCapture(e.pointerId);
  }
  function onPointerMove(e: PointerEvent) {
    if (capturedPointerId != e.pointerId) return;

    e.preventDefault();
    e.stopPropagation();

    x = Math.min(width / 2, Math.max(-width / 2, x + e.movementX));
    y = Math.min(height / 2, Math.max(-height / 2, y + e.movementY));

    ws?.send(
      JSON.stringify({
        id,
        x,
        y,
      }),
    );
  }
</script>

<div
  bind:this={element}
  onpointerdown={onPointerDown}
  onpointerup={onPointerUp}
  onpointermove={onPointerMove}
  style={`transform: translate(${vis_x}px, ${vis_y}px)`}
  class="absolute flex h-40 w-40 touch-none select-none items-center justify-center rounded-full border-red-400 bg-red-400"
>
  Tracker {id}
</div>
