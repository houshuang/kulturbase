import { Z as store_get, U as head, _ as unsubscribe_stores, W as attr, Y as stringify, X as ensure_array_like } from "../../../../chunks/index2.js";
import { p as page } from "../../../../chunks/stores.js";
import { e as escape_html } from "../../../../chunks/context.js";
function getDatabase() {
  throw new Error("Database not initialized");
}
function getWork(id) {
  const db2 = getDatabase();
  const stmt = db2.prepare(`
		SELECT w.*, playwright.name as playwright_name
		FROM works w
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		WHERE w.id = ?
	`);
  stmt.bind([id]);
  let result = null;
  if (stmt.step()) {
    result = stmt.getAsObject();
  }
  stmt.free();
  return result;
}
const getPlay = getWork;
function getPerformance(id) {
  const db2 = getDatabase();
  const stmt = db2.prepare(`
		SELECT
			perf.*,
			w.title as work_title,
			w.playwright_id,
			w.work_type,
			w.category,
			playwright.name as playwright_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		LEFT JOIN works w ON perf.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		WHERE perf.id = ?
	`);
  stmt.bind([id]);
  let result = null;
  if (stmt.step()) {
    result = stmt.getAsObject();
  }
  stmt.free();
  return result;
}
function getPerformanceContributors(performanceId) {
  const db2 = getDatabase();
  const stmt = db2.prepare(`
		SELECT pp.*, p.name as person_name
		FROM performance_persons pp
		JOIN persons p ON pp.person_id = p.id
		WHERE pp.performance_id = ?
		ORDER BY
			CASE pp.role
				WHEN 'director' THEN 1
				WHEN 'playwright' THEN 2
				WHEN 'actor' THEN 3
				ELSE 4
			END,
			p.name
	`);
  stmt.bind([performanceId]);
  const results = [];
  while (stmt.step()) {
    results.push(stmt.getAsObject());
  }
  stmt.free();
  return results;
}
function getPerformanceMedia(performanceId) {
  const db2 = getDatabase();
  const stmt = db2.prepare(`
		SELECT *
		FROM episodes
		WHERE performance_id = ?
		ORDER BY prf_id ASC
	`);
  stmt.bind([performanceId]);
  const results = [];
  while (stmt.step()) {
    results.push(stmt.getAsObject());
  }
  stmt.free();
  return results;
}
function getOtherPerformances(workId, excludePerformanceId) {
  const db2 = getDatabase();
  const stmt = db2.prepare(`
		SELECT
			perf.*,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		WHERE perf.work_id = ? AND perf.id != ?
		ORDER BY perf.year DESC
	`);
  stmt.bind([workId, excludePerformanceId]);
  const results = [];
  while (stmt.step()) {
    results.push(stmt.getAsObject());
  }
  stmt.free();
  return results;
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let performanceId, contributorGroups, directorName;
    let performance = null;
    let work = null;
    let contributors = [];
    let media = [];
    let otherPerformances = [];
    let loading = true;
    let error = null;
    function loadPerformance() {
      loading = true;
      error = null;
      work = null;
      otherPerformances = [];
      try {
        performance = getPerformance(performanceId);
        if (performance) {
          contributors = getPerformanceContributors(performanceId);
          media = getPerformanceMedia(performanceId);
          if (performance.work_id) {
            work = getPlay(performance.work_id);
            otherPerformances = getOtherPerformances(performance.work_id, performanceId);
          }
        } else {
          error = "Opptak ikke funnet";
        }
        loading = false;
      } catch (e) {
        error = e instanceof Error ? e.message : "Ukjent feil";
        loading = false;
      }
    }
    function formatDuration(seconds) {
      if (!seconds) return "";
      const h = Math.floor(seconds / 3600);
      const m = Math.floor(seconds % 3600 / 60);
      if (h > 0) return `${h}t ${m}m`;
      return `${m} min`;
    }
    function formatDurationLong(seconds) {
      if (!seconds) return "";
      const h = Math.floor(seconds / 3600);
      const m = Math.floor(seconds % 3600 / 60);
      if (h > 0) return `${h} time${h > 1 ? "r" : ""} ${m} min`;
      return `${m} minutter`;
    }
    function hasImage(url) {
      return !!url && url.length > 0;
    }
    function getRoleLabel(role) {
      const labels = {
        director: "Regi",
        actor: "Skuespillere",
        playwright: "Manus",
        composer: "Komponist",
        set_designer: "Scenografi",
        costume_designer: "Kostymer",
        producer: "Produsent",
        other: "Annet"
      };
      return labels[role || ""] || role || "Ukjent rolle";
    }
    function groupContributors(contribs) {
      const groups = {};
      for (const c of contribs) {
        const role = c.role || "other";
        if (!groups[role]) groups[role] = [];
        groups[role].push(c);
      }
      return groups;
    }
    function getDirectorName() {
      const director = contributors.find((c) => c.role === "director");
      return director?.person_name || null;
    }
    performanceId = parseInt(store_get($$store_subs ??= {}, "$page", page).params.id || "0");
    if (performanceId) {
      loadPerformance();
    }
    contributorGroups = groupContributors(contributors);
    directorName = getDirectorName();
    head("did11h", $$renderer2, ($$renderer3) => {
      if (performance) {
        $$renderer3.push("<!--[-->");
        $$renderer3.title(($$renderer4) => {
          $$renderer4.push(`<title>${escape_html(performance.title || work?.title || "Opptak")} (${escape_html(performance.year)}) - Kulturperler</title>`);
        });
      } else {
        $$renderer3.push("<!--[!-->");
      }
      $$renderer3.push(`<!--]-->`);
    });
    if (loading) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-did11h">Laster...</div>`);
    } else {
      $$renderer2.push("<!--[!-->");
      if (error) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="error svelte-did11h">${escape_html(error)}</div>`);
      } else {
        $$renderer2.push("<!--[!-->");
        if (performance) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<article class="performance-detail svelte-did11h"><a href="/" class="back-link svelte-did11h">← Tilbake til oversikt</a> <div class="performance-header svelte-did11h">`);
          if (media.length === 1) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<a${attr("href", media[0].nrk_url || `https://tv.nrk.no/se?v=${media[0].prf_id}`)} target="_blank" rel="noopener" class="performance-image playable svelte-did11h">`);
            if (hasImage(performance.image_url)) {
              $$renderer2.push("<!--[-->");
              $$renderer2.push(`<img${attr("src", performance.image_url)}${attr("alt", performance.title || "")} class="svelte-did11h"/>`);
            } else {
              $$renderer2.push("<!--[!-->");
              $$renderer2.push(`<div class="image-placeholder svelte-did11h"><svg viewBox="0 0 24 24" fill="currentColor" class="placeholder-icon svelte-did11h"><path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"></path></svg></div>`);
            }
            $$renderer2.push(`<!--]--> <div class="header-play-icon svelte-did11h"><svg viewBox="0 0 24 24" fill="currentColor" class="svelte-did11h"><path d="M8 5v14l11-7z"></path></svg></div> `);
            if (media[0].duration_seconds) {
              $$renderer2.push("<!--[-->");
              $$renderer2.push(`<span class="header-duration svelte-did11h">${escape_html(formatDuration(media[0].duration_seconds))}</span>`);
            } else {
              $$renderer2.push("<!--[!-->");
            }
            $$renderer2.push(`<!--]--></a>`);
          } else {
            $$renderer2.push("<!--[!-->");
            $$renderer2.push(`<div class="performance-image svelte-did11h">`);
            if (hasImage(performance.image_url)) {
              $$renderer2.push("<!--[-->");
              $$renderer2.push(`<img${attr("src", performance.image_url)}${attr("alt", performance.title || "")} class="svelte-did11h"/>`);
            } else {
              $$renderer2.push("<!--[!-->");
              $$renderer2.push(`<div class="image-placeholder svelte-did11h"><svg viewBox="0 0 24 24" fill="currentColor" class="placeholder-icon svelte-did11h"><path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"></path></svg></div>`);
            }
            $$renderer2.push(`<!--]--></div>`);
          }
          $$renderer2.push(`<!--]--> <div class="performance-info svelte-did11h"><h1 class="svelte-did11h">${escape_html(performance.title || work?.title || "Ukjent tittel")} `);
          if (performance.medium === "radio") {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<span class="medium-badge radio svelte-did11h">Radioteater</span>`);
          } else {
            $$renderer2.push("<!--[!-->");
            $$renderer2.push(`<span class="medium-badge tv svelte-did11h">Fjernsynsteater</span>`);
          }
          $$renderer2.push(`<!--]--></h1> <div class="meta-line svelte-did11h">`);
          if (performance.year) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<span class="year svelte-did11h">${escape_html(performance.year)}</span>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (performance.total_duration) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<span class="duration">${escape_html(formatDurationLong(performance.total_duration))}</span>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (directorName) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<span class="director">Regi: ${escape_html(directorName)}</span>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--></div> `);
          if (work) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<div class="work-preview svelte-did11h"><div class="work-preview-header svelte-did11h"><span class="label svelte-did11h">Fra stykket (${escape_html(otherPerformances.length + 1)} opptak)</span> <a${attr("href", `/play/${stringify(work.id)}`)} class="work-link svelte-did11h">Se mer →</a></div> <h2 class="svelte-did11h"><a${attr("href", `/play/${stringify(work.id)}`)} class="svelte-did11h">${escape_html(work.title)}</a> `);
            if (work.year_written) {
              $$renderer2.push("<!--[-->");
              $$renderer2.push(`<span class="year-written svelte-did11h">(${escape_html(work.year_written)})</span>`);
            } else {
              $$renderer2.push("<!--[!-->");
            }
            $$renderer2.push(`<!--]--></h2> `);
            if (performance.playwright_name) {
              $$renderer2.push("<!--[-->");
              $$renderer2.push(`<p class="playwright svelte-did11h">av <a${attr("href", `/person/${stringify(performance.playwright_id)}`)} class="svelte-did11h">${escape_html(performance.playwright_name)}</a></p>`);
            } else {
              $$renderer2.push("<!--[!-->");
            }
            $$renderer2.push(`<!--]--></div>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (performance.description) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<p class="description svelte-did11h">${escape_html(performance.description)}</p>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--></div></div> `);
          if (media.length > 1) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<section class="media-section svelte-did11h"><h2 class="svelte-did11h">Se alle deler (${escape_html(media.length)})</h2> <div class="media-grid svelte-did11h"><!--[-->`);
            const each_array = ensure_array_like(media);
            for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
              let item = each_array[$$index];
              $$renderer2.push(`<a${attr("href", item.nrk_url || `https://tv.nrk.no/se?v=${item.prf_id}`)} target="_blank" rel="noopener" class="media-card svelte-did11h"><div class="media-thumbnail svelte-did11h">`);
              if (hasImage(item.image_url)) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", item.image_url)}${attr("alt", item.title)} loading="lazy" class="svelte-did11h"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="image-placeholder small svelte-did11h"><svg viewBox="0 0 24 24" fill="currentColor" class="placeholder-icon svelte-did11h"><path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"></path></svg></div>`);
              }
              $$renderer2.push(`<!--]--> <div class="play-icon svelte-did11h"><svg viewBox="0 0 24 24" fill="currentColor" class="svelte-did11h"><path d="M8 5v14l11-7z"></path></svg></div> `);
              if (item.duration_seconds) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="media-duration svelte-did11h">${escape_html(formatDuration(item.duration_seconds))}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div> <div class="media-info svelte-did11h">`);
              if (media.length > 1) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="part-label svelte-did11h">`);
                if (item.part_number) {
                  $$renderer2.push("<!--[-->");
                  $$renderer2.push(`Del ${escape_html(item.part_number)}`);
                  if (item.total_parts) {
                    $$renderer2.push("<!--[-->");
                    $$renderer2.push(`/${escape_html(item.total_parts)}`);
                  } else {
                    $$renderer2.push("<!--[!-->");
                  }
                  $$renderer2.push(`<!--]-->`);
                } else {
                  $$renderer2.push("<!--[!-->");
                  if (item.media_type === "intro") {
                    $$renderer2.push("<!--[-->");
                    $$renderer2.push(`Introduksjon`);
                  } else {
                    $$renderer2.push("<!--[!-->");
                    $$renderer2.push(`${escape_html(item.title)}`);
                  }
                  $$renderer2.push(`<!--]-->`);
                }
                $$renderer2.push(`<!--]--></span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> <span class="watch-label svelte-did11h">${escape_html(performance?.medium === "radio" ? "Lytt på NRK Radio" : "Se på NRK TV")}</span></div></a>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (Object.keys(contributorGroups).length > 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<section class="contributors svelte-did11h"><h2 class="svelte-did11h">Medvirkende</h2> <div class="contributor-groups svelte-did11h"><!--[-->`);
            const each_array_1 = ensure_array_like(Object.entries(contributorGroups));
            for (let $$index_2 = 0, $$length = each_array_1.length; $$index_2 < $$length; $$index_2++) {
              let [role, contribs] = each_array_1[$$index_2];
              $$renderer2.push(`<div class="contributor-group svelte-did11h"><h3 class="svelte-did11h">${escape_html(getRoleLabel(role))}</h3> <ul class="svelte-did11h"><!--[-->`);
              const each_array_2 = ensure_array_like(contribs);
              for (let $$index_1 = 0, $$length2 = each_array_2.length; $$index_1 < $$length2; $$index_1++) {
                let c = each_array_2[$$index_1];
                $$renderer2.push(`<li class="svelte-did11h"><a${attr("href", `/person/${stringify(c.person_id)}`)} class="svelte-did11h">${escape_html(c.person_name)}</a> `);
                if (c.character_name) {
                  $$renderer2.push("<!--[-->");
                  $$renderer2.push(`<span class="character svelte-did11h">som ${escape_html(c.character_name)}</span>`);
                } else {
                  $$renderer2.push("<!--[!-->");
                }
                $$renderer2.push(`<!--]--></li>`);
              }
              $$renderer2.push(`<!--]--></ul></div>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (otherPerformances.length > 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<section class="other-performances svelte-did11h"><h2 class="svelte-did11h">Andre opptak av ${escape_html(work?.title || "dette stykket")}</h2> <div class="other-performances-grid svelte-did11h"><!--[-->`);
            const each_array_3 = ensure_array_like(otherPerformances);
            for (let $$index_3 = 0, $$length = each_array_3.length; $$index_3 < $$length; $$index_3++) {
              let other = each_array_3[$$index_3];
              $$renderer2.push(`<a${attr("href", `/performance/${stringify(other.id)}`)} class="other-performance-card svelte-did11h"><div class="other-thumbnail svelte-did11h">`);
              if (hasImage(other.image_url)) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", other.image_url)}${attr("alt", other.title || "")} loading="lazy" class="svelte-did11h"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="image-placeholder small svelte-did11h"><svg viewBox="0 0 24 24" fill="currentColor" class="placeholder-icon svelte-did11h"><path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"></path></svg></div>`);
              }
              $$renderer2.push(`<!--]--></div> <div class="other-info svelte-did11h"><span class="other-year svelte-did11h">${escape_html(other.year)}</span> `);
              if (other.director_name) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="other-director svelte-did11h">Regi: ${escape_html(other.director_name)}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (other.total_duration) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="other-duration svelte-did11h">${escape_html(formatDuration(other.total_duration))}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div></a>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--></article>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]-->`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]-->`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
