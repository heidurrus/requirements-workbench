<script>
  // A pop-up button with a menu: one of N (shows the value) or a list of commands.
  import Icon from "./Icon.svelte";

  // items: [{ value, label, hint, icon, danger, sep, disabled }]
  let { label = "", value = undefined, text = "", items = [], onpick, align = "left", cls = "popbtn", icon = "", title = "",
        ariaLabel = "", chevron = "updown", disabled = false } = $props();
  let open = $state(false);
  let root = $state(null);
  const current = $derived(items.find(i => i.value === value));

  function pick(item) {
    open = false;
    if (!item.disabled) onpick?.(item.value, item);
  }
  function onDoc(e) { if (open && root && !root.contains(e.target)) open = false; }
  function onKey(e) {
    if (!open) return;
    if (e.key === "Escape") { e.stopPropagation(); open = false; root?.querySelector("button")?.focus(); return; }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const list = [...root.querySelectorAll(".menu-item:not(:disabled)")];
      const i = list.indexOf(document.activeElement);
      (list[(i + (e.key === "ArrowDown" ? 1 : -1) + list.length) % list.length] || list[0])?.focus();
    }
  }
</script>

<svelte:document onmousedown={onDoc} />

<span class="pop" bind:this={root} onkeydown={onKey} role="presentation">
  <button class={cls} type="button" aria-haspopup="menu" aria-expanded={open} aria-label={ariaLabel || undefined} {title} {disabled}
          onclick={() => (open = !open)}>
    {#if icon}<Icon name={icon} size={14} />{/if}
    {#if label}<span class="lab">{label}</span>{/if}
    {#if text || current}<span class="trunc">{text || current.label}</span>{/if}
    {#if chevron}<Icon name={chevron} size={12} />{/if}
  </button>
  {#if open}
    <div class="menu" class:right={align === "right"} role="menu">
      {#each items as item, i (i)}
        {#if item.sep}<hr />
        {:else if item.heading}<div class="menu-label">{item.heading}</div>
        {:else}
          <button class="menu-item" class:on={value !== undefined && item.value === value} class:danger-text={item.danger} role="menuitem"
                  disabled={item.disabled} onclick={() => pick(item)}>
            {#if value !== undefined}<span class="tick">{#if item.value === value}<Icon name="check" size={12} />{/if}</span>{/if}
            {#if item.icon}<Icon name={item.icon} size={14} />{/if}
            <span class="grow">{item.label}</span>
            {#if item.hint}<span class="t3 num">{item.hint}</span>{/if}
          </button>
        {/if}
      {/each}
    </div>
  {/if}
</span>

<style>
  .pop { position: relative; display: inline-flex; min-width: 0; }
  .menu { top: calc(100% + 4px); left: 0; }
  .menu.right { left: auto; right: 0; }
  .menu-item:disabled { opacity: .4; cursor: default; }
</style>
