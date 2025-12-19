import { V as attr_class, W as attr, X as ensure_array_like, Y as stringify } from "../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../chunks/exports.js";
import "../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../chunks/state.svelte.js";
import { e as escape_html } from "../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let filteredAuthors;
    let activeTab = "opptak";
    let performances = [];
    let matchingAuthors = [];
    let directors = [];
    let playwrights = [];
    let yearRange = { min: 1960, max: 2016 };
    let mediumCounts = { tv: 0, radio: 0 };
    let showTv = true;
    let showRadio = true;
    let filters = {
      query: "",
      yearFrom: void 0,
      yearTo: void 0,
      playwrightId: void 0,
      directorId: void 0
    };
    let totalCount = 0;
    let playCount = 0;
    let authors = [];
    let authorCount = 0;
    function formatDuration(seconds) {
      if (!seconds) return "";
      const h = Math.floor(seconds / 3600);
      const m = Math.floor(seconds % 3600 / 60);
      if (h > 0) return `${h}t ${m}m`;
      return `${m} min`;
    }
    function getImageUrl(url) {
      if (!url) return "/placeholder.jpg";
      return url;
    }
    filteredAuthors = authors.filter((a) => true);
    filteredAuthors.filter((a) => a.birth_year);
    $$renderer2.push(`<div class="page-container svelte-1uha8ag"><nav class="tabs svelte-1uha8ag"><button${attr_class("svelte-1uha8ag", void 0, {
      "active": (
        // Update URL with search filters
        // Clear all filter params from URL
        activeTab === "opptak"
      )
    })}>Opptak <span class="count svelte-1uha8ag">(${escape_html(mediumCounts.tv + mediumCounts.radio)})</span></button> <button${attr_class("svelte-1uha8ag", void 0, { "active": activeTab === "skuespill" })}>Skuespill <span class="count svelte-1uha8ag">(${escape_html(playCount)})</span></button> <button${attr_class("svelte-1uha8ag", void 0, { "active": activeTab === "forfattere" })}>Forfattere <span class="count svelte-1uha8ag">(${escape_html(authorCount)})</span></button></nav> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="browse-page svelte-1uha8ag"><aside class="filters svelte-1uha8ag"><h2 class="svelte-1uha8ag">Filtrer</h2> <div class="filter-group svelte-1uha8ag"><label for="search" class="svelte-1uha8ag">Fritekst</label> <input type="search" id="search"${attr("value", filters.query)} placeholder="Tittel, beskrivelse..." class="svelte-1uha8ag"/></div> <div class="filter-group svelte-1uha8ag"><span class="filter-label svelte-1uha8ag">År (${escape_html(yearRange.min)} - ${escape_html(yearRange.max)})</span> <div class="year-range svelte-1uha8ag"><input type="number"${attr("value", filters.yearFrom)} placeholder="Fra"${attr("min", yearRange.min)}${attr("max", yearRange.max)} class="svelte-1uha8ag"/> <span>-</span> <input type="number"${attr("value", filters.yearTo)} placeholder="Til"${attr("min", yearRange.min)}${attr("max", yearRange.max)} class="svelte-1uha8ag"/></div></div> `);
      if (playwrights.length > 0) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="filter-group svelte-1uha8ag"><label for="playwright" class="svelte-1uha8ag">Dramatiker</label> `);
        $$renderer2.select(
          { id: "playwright", value: filters.playwrightId, class: "" },
          ($$renderer3) => {
            $$renderer3.option({ value: void 0 }, ($$renderer4) => {
              $$renderer4.push(`Alle`);
            });
            $$renderer3.push(`<!--[-->`);
            const each_array = ensure_array_like(playwrights);
            for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
              let p = each_array[$$index];
              $$renderer3.option({ value: p.id }, ($$renderer4) => {
                $$renderer4.push(`${escape_html(p.name)}`);
              });
            }
            $$renderer3.push(`<!--]-->`);
          },
          "svelte-1uha8ag"
        );
        $$renderer2.push(`</div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> `);
      if (directors.length > 0) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="filter-group svelte-1uha8ag"><label for="director" class="svelte-1uha8ag">Regissør</label> `);
        $$renderer2.select(
          { id: "director", value: filters.directorId, class: "" },
          ($$renderer3) => {
            $$renderer3.option({ value: void 0 }, ($$renderer4) => {
              $$renderer4.push(`Alle`);
            });
            $$renderer3.push(`<!--[-->`);
            const each_array_1 = ensure_array_like(directors);
            for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
              let d = each_array_1[$$index_1];
              $$renderer3.option({ value: d.id }, ($$renderer4) => {
                $$renderer4.push(`${escape_html(d.name)}`);
              });
            }
            $$renderer3.push(`<!--]-->`);
          },
          "svelte-1uha8ag"
        );
        $$renderer2.push(`</div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> <div class="filter-group svelte-1uha8ag"><span class="filter-label svelte-1uha8ag">Medium</span> <div class="medium-checkboxes svelte-1uha8ag"><label class="checkbox-label svelte-1uha8ag"><input type="checkbox"${attr("checked", showTv, true)} class="svelte-1uha8ag"/> <span class="medium-icon tv svelte-1uha8ag">TV</span> Fjernsynsteater `);
      {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></label> <label class="checkbox-label svelte-1uha8ag"><input type="checkbox"${attr("checked", showRadio, true)} class="svelte-1uha8ag"/> <span class="medium-icon radio svelte-1uha8ag">R</span> Radioteater `);
      {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></label></div></div> <button class="clear-btn svelte-1uha8ag">Nullstill filter</button></aside> <section class="results">`);
      if (matchingAuthors.length > 0) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="author-results svelte-1uha8ag"><h3 class="svelte-1uha8ag">Dramatikere</h3> <div class="author-cards svelte-1uha8ag"><!--[-->`);
        const each_array_2 = ensure_array_like(matchingAuthors);
        for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
          let author = each_array_2[$$index_2];
          $$renderer2.push(`<a${attr("href", `/person/${stringify(author.id)}`)} class="author-card svelte-1uha8ag"><div class="author-card-info svelte-1uha8ag"><span class="author-card-name svelte-1uha8ag">${escape_html(author.name)}</span> `);
          if (author.birth_year) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<span class="author-card-dates svelte-1uha8ag">${escape_html(author.birth_year)}–${escape_html(author.death_year || "")}</span>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> <span class="author-card-count svelte-1uha8ag">${escape_html(author.play_count)} stykker</span></div></a>`);
        }
        $$renderer2.push(`<!--]--></div></div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> <div class="results-header svelte-1uha8ag"><h2 class="svelte-1uha8ag">${escape_html(totalCount)} opptak</h2> `);
      {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></div> <div class="performances-grid svelte-1uha8ag"><!--[-->`);
      const each_array_3 = ensure_array_like(performances);
      for (let $$index_3 = 0, $$length = each_array_3.length; $$index_3 < $$length; $$index_3++) {
        let perf = each_array_3[$$index_3];
        $$renderer2.push(`<a${attr("href", `/performance/${stringify(perf.id)}`)} class="performance-card svelte-1uha8ag"><div class="performance-image svelte-1uha8ag"><img${attr("src", getImageUrl(perf.image_url))}${attr("alt", perf.title || "")} loading="lazy" class="svelte-1uha8ag"/> `);
        if (perf.total_duration) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="duration svelte-1uha8ag">${escape_html(formatDuration(perf.total_duration))}</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--> `);
        if (perf.media_count && perf.media_count > 1) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="parts-badge svelte-1uha8ag">${escape_html(perf.media_count)} deler</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--> `);
        if (perf.medium === "radio") {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="medium-badge radio svelte-1uha8ag">Radio</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--></div> <div class="performance-info svelte-1uha8ag"><h3 class="svelte-1uha8ag">${escape_html(perf.work_title || perf.title || "Ukjent tittel")}</h3> `);
        if (perf.year) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="year svelte-1uha8ag">${escape_html(perf.year)}</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--> `);
        if (perf.director_name) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<span class="director svelte-1uha8ag">Regi: ${escape_html(perf.director_name)}</span>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--></div></a>`);
      }
      $$renderer2.push(`<!--]--></div> `);
      if (performances.length === 0) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="no-results svelte-1uha8ag"><p>Ingen opptak funnet med disse filtrene.</p></div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> `);
      {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></section></div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
