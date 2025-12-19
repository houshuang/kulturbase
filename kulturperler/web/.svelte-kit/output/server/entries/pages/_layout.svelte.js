import { U as head } from "../../chunks/index2.js";
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    head("12qhfyh", $$renderer2, ($$renderer3) => {
      $$renderer3.push(`<link rel="preconnect" href="https://gfx.nrk.no"/>`);
    });
    $$renderer2.push(`<div class="app svelte-12qhfyh"><header class="svelte-12qhfyh"><nav class="svelte-12qhfyh"><a href="/" class="logo svelte-12qhfyh">Kulturbase.no</a></nav></header> <main class="svelte-12qhfyh">`);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-12qhfyh"><p>Laster database...</p></div>`);
    }
    $$renderer2.push(`<!--]--></main> <footer class="svelte-12qhfyh"><p>Data fra <a href="https://tv.nrk.no" target="_blank" rel="noopener" class="svelte-12qhfyh">NRK TV</a>.
			Beriket med data fra <a href="https://sceneweb.no" target="_blank" rel="noopener" class="svelte-12qhfyh">Sceneweb</a> og <a href="https://www.wikidata.org" target="_blank" rel="noopener" class="svelte-12qhfyh">Wikidata</a>.</p></footer></div>`);
  });
}
export {
  _layout as default
};
