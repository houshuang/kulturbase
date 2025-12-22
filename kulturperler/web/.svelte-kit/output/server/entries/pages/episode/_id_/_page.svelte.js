import { U as store_get, V as head, Z as unsubscribe_stores } from "../../../../chunks/index2.js";
import { p as page } from "../../../../chunks/stores.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let contributors = [];
    function groupContributors(contribs) {
      const groups = {};
      for (const c of contribs) {
        const role = c.role || "other";
        if (!groups[role]) groups[role] = [];
        groups[role].push(c);
      }
      return groups;
    }
    store_get($$store_subs ??= {}, "$page", page).params.id || "";
    groupContributors(contributors);
    head("1gd4mte", $$renderer2, ($$renderer3) => {
      {
        $$renderer3.push("<!--[!-->");
      }
      $$renderer3.push(`<!--]-->`);
    });
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-1gd4mte">Laster...</div>`);
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
