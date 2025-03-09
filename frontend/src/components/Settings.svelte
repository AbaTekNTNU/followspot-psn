<script lang="ts">
  import * as Drawer from "$lib/components/ui/drawer/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import TrackerSetting from "./TrackerSetting.svelte";

  const addTracker = async () => {
    const response = await fetch("/tracker", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        id: 6,
      }),
    });

    console.log(response);
  };

  const deleteTracker = async () => {
    const response = await fetch("/tracker", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        id: 6,
      }),
    });
    console.log(response);
  };
</script>


<Drawer.Root>
  <Drawer.Trigger asChild let:builder>
    <Button builders={[builder]} variant="outline">Settings</Button>
  </Drawer.Trigger>
  <Drawer.Content>
    <Drawer.Header>
      <Drawer.Title>Are you sure absolutely sure?</Drawer.Title>
      <Drawer.Description>This action cannot be undone.</Drawer.Description>
    </Drawer.Header>
    <div class="flex items-center justify-evenly">
      <TrackerSetting action={addTracker} text="Add Tracker" />
      <TrackerSetting action={deleteTracker} text="Delete Tracker" />
    </div>
  </Drawer.Content>
</Drawer.Root>
