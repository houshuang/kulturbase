import { Z as store_get, U as head, _ as unsubscribe_stores } from "../../../../chunks/index2.js";
import { p as page } from "../../../../chunks/stores.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    parseInt(store_get($$store_subs ??= {}, "$page", page).params.id || "0");
    head("13eo3pq", $$renderer2, ($$renderer3) => {
      {
        $$renderer3.push("<!--[!-->");
      }
      $$renderer3.push(`<!--]-->`);
    });
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-13eo3pq">Laster...</div>`);
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
