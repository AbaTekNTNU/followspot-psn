<script lang="ts">
  import Button from "./ui/button/button.svelte";
  import Input from "./ui/input/input.svelte";

  type Props = {
    text: string;
    action: (arg: number) => void;
    value: number;
  };

  let { action, text, value = $bindable() }: Props = $props();
</script>

<div>
  <h2>{text}</h2>
  <Input placeholder={"1"} type="tel" bind:value />
  <Button onclick={() => action(value)}>Submit</Button>
</div>
