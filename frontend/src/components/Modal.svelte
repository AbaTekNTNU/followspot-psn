<script lang="ts">
  type Props = {
    action: () => void;
  };

  let { action }: Props = $props();

  let dialog: HTMLDialogElement;
  const openModal = () => {
    dialog.showModal();
  };
</script>

<button class="mb-24 rounded-md bg-red-500 p-2" onclick={openModal}>
  Change mode
</button>

<dialog
  open={false}
  bind:this={dialog}
  class="absolute left-0 top-0 z-50 m-0 h-full max-h-full w-full max-w-full p-0 open:bg-black/80"
>
  <div class="flex h-full w-full flex-col items-center justify-center">
    <h1 class="text-center text-8xl text-red-600">THIS GONNA FUCK THINGS UP</h1>
    <div class="flex items-center justify-center gap-6">
      <button class="rounded-md bg-gray-400 p-4" onclick={() => dialog.close()}
        >Close</button
      >
      <button
        class="rounded-md bg-red-500 p-4"
        onclick={() => {
          action();
          dialog.close();
        }}>Change mode</button
      >
    </div>
  </div>
</dialog>
