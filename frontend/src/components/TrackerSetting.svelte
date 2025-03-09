<script lang="ts">
  import Button from "./ui/button/button.svelte";
  import Input from "./ui/input/input.svelte";

  type Props = {
    text: string;
    action: () => void;
  };

  let { action, text }: Props = $props();
</script>

<div>
  <h2>{text}</h2>
  <Input placeholder={"1"} type="tel" />
  <Button onclick={action}>Submit</Button>
</div>
