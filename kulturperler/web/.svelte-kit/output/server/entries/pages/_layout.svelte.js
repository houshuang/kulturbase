import { U as store_get, V as head, W as ensure_array_like, X as attr, Y as attr_class, Z as unsubscribe_stores } from "../../chunks/index2.js";
import { p as page } from "../../chunks/stores.js";
import { e as escape_html } from "../../chunks/context.js";
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let currentPath;
    const navItems = [
      { href: "/", label: "Hjem", exact: true },
      { href: "/teater", label: "Teater" },
      { href: "/opera", label: "Opera" },
      { href: "/dramaserier", label: "Dramaserier" },
      { href: "/konserter", label: "Konserter" },
      { href: "/skapere", label: "Skapere" }
    ];
    function isActive(href, exact = false) {
      if (exact) return currentPath === href;
      return currentPath === href || currentPath.startsWith(href + "/");
    }
    currentPath = store_get($$store_subs ??= {}, "$page", page).url.pathname;
    head("12qhfyh", $$renderer2, ($$renderer3) => {
      $$renderer3.push(`<link rel="preconnect" href="https://gfx.nrk.no"/>`);
    });
    $$renderer2.push(`<div class="app svelte-12qhfyh"><header class="svelte-12qhfyh"><div class="header-content svelte-12qhfyh"><a href="/" class="logo svelte-12qhfyh">Kulturbase.no</a> <nav class="main-nav svelte-12qhfyh"><!--[-->`);
    const each_array = ensure_array_like(navItems);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let item = each_array[$$index];
      $$renderer2.push(`<a${attr("href", item.href)}${attr_class("nav-link svelte-12qhfyh", void 0, { "active": isActive(item.href, item.exact) })}>${escape_html(item.label)}</a>`);
    }
    $$renderer2.push(`<!--]--></nav></div></header> <main class="svelte-12qhfyh">`);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-12qhfyh"><p>Laster database...</p></div>`);
    }
    $$renderer2.push(`<!--]--></main> <footer class="svelte-12qhfyh"><p>Data fra <a href="https://tv.nrk.no" target="_blank" rel="noopener" class="svelte-12qhfyh">NRK TV</a>.
			Beriket med data fra <a href="https://sceneweb.no" target="_blank" rel="noopener" class="svelte-12qhfyh">Sceneweb</a> og <a href="https://www.wikidata.org" target="_blank" rel="noopener" class="svelte-12qhfyh">Wikidata</a>.</p></footer></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _layout as default
};
