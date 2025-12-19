import { U as head } from "../../../chunks/index2.js";
import { e as escape_html } from "../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let filteredPlaywrights;
    let allPlaywrights = [];
    function filterAndSort(playwrights, query, nationality, sort, direction) {
      let result = [...playwrights];
      result.sort((a, b) => {
        let cmp = 0;
        {
          cmp = a.performance_count - b.performance_count;
        }
        return -cmp;
      });
      return result;
    }
    filteredPlaywrights = filterAndSort(allPlaywrights);
    {
      if (allPlaywrights.length > 0) {
        const birthYears = allPlaywrights.filter((p) => p.birth_year).map((p) => p.birth_year);
        if (birthYears.length > 0) {
          Math.floor(Math.min(...birthYears) / 10) * 10;
          Math.ceil(Math.max(...birthYears) / 10) * 10;
        }
      }
    }
    head("1aro8zh", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Dramatikere - Kulturperler</title>`);
      });
    });
    $$renderer2.push(`<div class="persons-page svelte-1aro8zh"><header class="page-header svelte-1aro8zh"><a href="/" class="back-link svelte-1aro8zh">← Tilbake</a> <h1 class="svelte-1aro8zh">Dramatikere</h1> <p class="subtitle svelte-1aro8zh">${escape_html(filteredPlaywrights.length)} av ${escape_html(allPlaywrights.length)} dramatikere</p></header> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-1aro8zh">Laster...</div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
