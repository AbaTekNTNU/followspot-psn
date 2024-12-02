<script lang="ts">
  type Props = {
    id: number;
    x: number;
    y: number;
    ws: WebSocket | null;
  };

  let {
    id = $bindable(),
    x = $bindable(),
    y = $bindable(),
    ws = $bindable(),
  }: Props = $props();

  let element: HTMLElement;

  let capturedPointerId: number | null = $state(null);

  function onPointerDown(e: PointerEvent) {
    element.setPointerCapture(e.pointerId);
    capturedPointerId = e.pointerId;
  }
  function onPointerUp(e: PointerEvent) {
    capturedPointerId = null;
    element.releasePointerCapture(e.pointerId);
  }
  function onPointerMove(e: PointerEvent) {
    if (capturedPointerId != e.pointerId) return;

    e.preventDefault();
    e.stopPropagation();

    x += e.movementX;
    y += e.movementY;

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
  style={`transform: translate(${x}px, ${y}px)`}
  class="absolute flex h-40 w-40 touch-none items-center justify-center rounded-full border-red-400 bg-red-400"
>
  Tracker {id}
</div>
