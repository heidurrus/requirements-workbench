<script>
  // A stack of at most two toasts, bottom centre of the content area; it sits
  // above the bulk bar when one is visible (body.has-bulk).
  import { app, dismissToast } from "../lib/state.svelte.js";

  function act(item) {
    dismissToast(item.id);
    item.onAction && item.onAction();
  }
</script>

<div class="toasts">
  {#each app.toasts as item (item.id)}
    <div class="toast {item.kind}" role="status">
      <span>{item.message}</span>
      {#if item.action}
        <button class="btn btn-sm" onclick={() => act(item)}>{item.action}</button>
      {/if}
    </div>
  {/each}
</div>
