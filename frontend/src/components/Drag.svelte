<script lang="ts">
  type Props = {
    id: number;
    x: number;
    y: number;
    ws: WebSocket | null;
    parent: HTMLElement;
  };

  let {
    id = $bindable(),
    x = $bindable(),
    y = $bindable(),
    ws = $bindable(),
    parent,
  }: Props = $props();

  let element: HTMLElement;

  let vis_x = $state(0);

  let vis_y = $state(0);

  $effect(() => {
    vis_x = x + (parent.clientWidth ?? 0) / 2 - (element.clientWidth ?? 0) / 2;

    vis_y =
      y + (parent.clientHeight ?? 0) / 2 - (element.clientHeight ?? 0) / 2;
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

    x = Math.min(
      parent.clientWidth / 2,
      Math.max(-parent.clientWidth / 2, x + e.movementX),
    );
    y = Math.min(
      parent.clientHeight / 2,
      Math.max(-parent.clientHeight / 2, y + e.movementY),
    );

    if (ws) {
      ws.send(
        JSON.stringify({
          id,
          x,
          y,
        }),
      );
    }
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
