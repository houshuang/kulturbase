import { U as store_get, V as head, X as attr, W as ensure_array_like, Y as attr_class, _ as stringify, Z as unsubscribe_stores } from "../../../../chunks/index2.js";
import { p as page } from "../../../../chunks/stores.js";
import { f as getComposerRoleLabel, h as getPerson, i as getDatabase, j as getNrkAboutPrograms } from "../../../../chunks/db.js";
import { e as escape_html } from "../../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let personId;
    let person = null;
    let isCreator = false;
    let creatorRoles = [];
    let allRoles = [];
    let stats = {
      worksAsPlaywright: 0,
      worksAsComposer: 0,
      worksAsLibrettist: 0,
      performanceCount: 0,
      directedCount: 0,
      actedCount: 0,
      conductedCount: 0
    };
    let worksWritten = [];
    let worksComposed = [];
    let librettos = [];
    let performancesByRole = [];
    let creatorWorkIds = /* @__PURE__ */ new Set();
    let nrkAboutPrograms = [];
    let performancesAbout = [];
    let episodesAbout = [];
    let loading = true;
    let error = null;
    function loadPerson() {
      loading = true;
      error = null;
      person = null;
      isCreator = false;
      creatorRoles = [];
      allRoles = [];
      stats = {
        worksAsPlaywright: 0,
        worksAsComposer: 0,
        worksAsLibrettist: 0,
        performanceCount: 0,
        directedCount: 0,
        actedCount: 0,
        conductedCount: 0
      };
      worksWritten = [];
      worksComposed = [];
      librettos = [];
      performancesByRole = [];
      creatorWorkIds = /* @__PURE__ */ new Set();
      nrkAboutPrograms = [];
      performancesAbout = [];
      episodesAbout = [];
      try {
        person = getPerson(personId);
        if (person) {
          const db = getDatabase();
          const creatorCheckStmt = db.prepare(`
					SELECT
						(SELECT COUNT(*) FROM works WHERE playwright_id = ?) as playwright_count,
						(SELECT COUNT(DISTINCT work_id) FROM work_composers WHERE person_id = ?) as composer_count,
						(SELECT COUNT(*) FROM works WHERE librettist_id = ?) as librettist_count
				`);
          creatorCheckStmt.bind([personId, personId, personId]);
          if (creatorCheckStmt.step()) {
            const counts = creatorCheckStmt.getAsObject();
            stats.worksAsPlaywright = counts.playwright_count;
            stats.worksAsComposer = counts.composer_count;
            stats.worksAsLibrettist = counts.librettist_count;
            if (counts.playwright_count > 0) creatorRoles.push("dramatiker");
            if (counts.composer_count > 0) creatorRoles.push("komponist");
            if (counts.librettist_count > 0) creatorRoles.push("librettist");
            isCreator = creatorRoles.length > 0;
          }
          creatorCheckStmt.free();
          if (isCreator) {
            const perfCountStmt = db.prepare(`
						SELECT COUNT(DISTINCT p.id) as count
						FROM performances p
						JOIN works w ON p.work_id = w.id
						LEFT JOIN work_composers wc ON w.id = wc.work_id
						WHERE w.playwright_id = ? OR wc.person_id = ? OR w.librettist_id = ?
					`);
            perfCountStmt.bind([personId, personId, personId]);
            if (perfCountStmt.step()) {
              stats.performanceCount = perfCountStmt.getAsObject().count;
            }
            perfCountStmt.free();
          }
          creatorWorkIds = /* @__PURE__ */ new Set();
          if (stats.worksAsPlaywright > 0) {
            const playsStmt = db.prepare(`
						SELECT w.id, w.title, w.year_written, w.work_type,
							(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as performance_count,
							(SELECT e.image_url FROM episodes e
							 JOIN performances pf ON e.performance_id = pf.id
							 WHERE pf.work_id = w.id LIMIT 1) as image_url
						FROM works w
						WHERE w.playwright_id = ?
						ORDER BY performance_count DESC, w.title
					`);
            playsStmt.bind([personId]);
            worksWritten = [];
            while (playsStmt.step()) {
              const work = playsStmt.getAsObject();
              worksWritten.push(work);
              creatorWorkIds.add(work.id);
            }
            playsStmt.free();
          }
          if (stats.worksAsComposer > 0) {
            const composerStmt = db.prepare(`
						SELECT w.id, w.title, w.year_written, w.work_type, wc.role as composer_role,
							(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as performance_count,
							(SELECT e.image_url FROM episodes e
							 JOIN performances pf ON e.performance_id = pf.id
							 WHERE pf.work_id = w.id LIMIT 1) as image_url
						FROM works w
						JOIN work_composers wc ON w.id = wc.work_id
						WHERE wc.person_id = ?
						ORDER BY performance_count DESC, w.title
					`);
            composerStmt.bind([personId]);
            worksComposed = [];
            while (composerStmt.step()) {
              const work = composerStmt.getAsObject();
              worksComposed.push(work);
              creatorWorkIds.add(work.id);
            }
            composerStmt.free();
          }
          if (stats.worksAsLibrettist > 0) {
            const librettoStmt = db.prepare(`
						SELECT w.id, w.title, w.year_written, w.work_type,
							(SELECT COUNT(*) FROM performances pf WHERE pf.work_id = w.id) as performance_count,
							(SELECT e.image_url FROM episodes e
							 JOIN performances pf ON e.performance_id = pf.id
							 WHERE pf.work_id = w.id LIMIT 1) as image_url
						FROM works w
						WHERE w.librettist_id = ?
						ORDER BY performance_count DESC, w.title
					`);
            librettoStmt.bind([personId]);
            librettos = [];
            while (librettoStmt.step()) {
              const work = librettoStmt.getAsObject();
              librettos.push(work);
              creatorWorkIds.add(work.id);
            }
            librettoStmt.free();
          }
          const rolesStmt = db.prepare(`
					SELECT DISTINCT role FROM performance_persons
					WHERE person_id = ? AND role NOT IN ('playwright', 'composer', 'librettist', 'forfatter')
				`);
          rolesStmt.bind([personId]);
          const roles = [];
          while (rolesStmt.step()) {
            roles.push(rolesStmt.getAsObject().role);
          }
          rolesStmt.free();
          performancesByRole = [];
          for (const role of roles) {
            const perfStmt = db.prepare(`
						SELECT DISTINCT
							p.id,
							p.work_id,
							COALESCE(w.title, p.title) as work_title,
							p.year,
							pw.name as playwright_name,
							pp.character_name,
							(SELECT e.image_url FROM episodes e WHERE e.performance_id = p.id LIMIT 1) as image_url
						FROM performances p
						JOIN performance_persons pp ON p.id = pp.performance_id
						LEFT JOIN works w ON p.work_id = w.id
						LEFT JOIN persons pw ON w.playwright_id = pw.id
						WHERE pp.person_id = ? AND pp.role = ?
						ORDER BY p.year DESC
					`);
            perfStmt.bind([personId, role]);
            const performances = [];
            while (perfStmt.step()) {
              const perf = perfStmt.getAsObject();
              if (perf.work_id && creatorWorkIds.has(perf.work_id)) {
                continue;
              }
              performances.push(perf);
            }
            perfStmt.free();
            if (performances.length > 0) {
              performancesByRole.push({ role, performances });
            }
          }
          nrkAboutPrograms = getNrkAboutPrograms(personId);
          const aboutStmt = db.prepare(`
					SELECT
						p.id,
						p.title,
						COALESCE(w.title, p.title) as work_title,
						p.year,
						p.total_duration,
						p.image_url,
						p.medium,
						(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = p.id) as episode_count
					FROM performances p
					LEFT JOIN works w ON p.work_id = w.id
					WHERE p.about_person_id = ?
					ORDER BY p.year DESC
				`);
          aboutStmt.bind([personId]);
          performancesAbout = [];
          while (aboutStmt.step()) {
            performancesAbout.push(aboutStmt.getAsObject());
          }
          aboutStmt.free();
          const episodesAboutStmt = db.prepare(`
					SELECT
						e.prf_id,
						e.title,
						p.title as perf_title,
						e.performance_id,
						e.year,
						e.duration_seconds,
						e.image_url,
						e.medium
					FROM episodes e
					LEFT JOIN performances p ON e.performance_id = p.id
					WHERE e.about_person_id = ?
					ORDER BY e.title
				`);
          episodesAboutStmt.bind([personId]);
          episodesAbout = [];
          while (episodesAboutStmt.step()) {
            episodesAbout.push(episodesAboutStmt.getAsObject());
          }
          episodesAboutStmt.free();
          allRoles = [];
          if (stats.worksAsPlaywright > 0) {
            allRoles.push({
              role: "playwright",
              label: "Dramatiker",
              count: stats.worksAsPlaywright
            });
          }
          if (stats.worksAsComposer > 0) {
            allRoles.push({
              role: "composer",
              label: "Komponist",
              count: stats.worksAsComposer
            });
          }
          if (stats.worksAsLibrettist > 0) {
            allRoles.push({
              role: "librettist",
              label: "Librettist",
              count: stats.worksAsLibrettist
            });
          }
          for (const group of performancesByRole) {
            if (group.performances.length > 0) {
              allRoles.push({
                role: group.role,
                label: getRoleLabelNoun(group.role),
                count: group.performances.length
              });
            }
          }
        } else {
          error = "Person ikke funnet";
        }
        loading = false;
      } catch (e) {
        error = e instanceof Error ? e.message : "Ukjent feil";
        loading = false;
      }
    }
    function getRoleLabel(role) {
      const labels = {
        director: "Regissert",
        actor: "Roller",
        playwright: "Stykker",
        composer: "Komponert",
        conductor: "Dirigert",
        soloist: "Solist",
        producer: "Produsert",
        set_designer: "Scenografi",
        costume_designer: "Kostymer",
        other: "Annet"
      };
      return labels[role] || role;
    }
    function getRoleLabelNoun(role) {
      const labels = {
        director: "Regissør",
        actor: "Skuespiller",
        conductor: "Dirigent",
        soloist: "Solist",
        producer: "Produsent",
        set_designer: "Scenograf",
        costume_designer: "Kostymedesigner",
        other: "Medvirkende"
      };
      return labels[role] || role;
    }
    function formatDuration(seconds) {
      if (!seconds) return "";
      const h = Math.floor(seconds / 3600);
      const m = Math.floor(seconds % 3600 / 60);
      if (h > 0) return `${h}t ${m}m`;
      return `${m} min`;
    }
    function getImageUrl(url, width = 320) {
      if (!url) return "";
      if (url.includes("gfx.nrk.no")) {
        return url.replace(/\/\d+$/, `/${width}`);
      }
      return url;
    }
    personId = parseInt(store_get($$store_subs ??= {}, "$page", page).params.id || "0");
    if (personId) loadPerson();
    head("13eo3pq", $$renderer2, ($$renderer3) => {
      if (person) {
        $$renderer3.push("<!--[-->");
        $$renderer3.title(($$renderer4) => {
          $$renderer4.push(`<title>${escape_html(person.name)} - Kulturbase.no</title>`);
        });
      } else {
        $$renderer3.push("<!--[!-->");
      }
      $$renderer3.push(`<!--]-->`);
    });
    if (loading) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-13eo3pq">Laster...</div>`);
    } else {
      $$renderer2.push("<!--[!-->");
      if (error) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="error svelte-13eo3pq">${escape_html(error)}</div>`);
      } else {
        $$renderer2.push("<!--[!-->");
        if (person) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<article class="person-detail svelte-13eo3pq"><a href="/" class="back-link svelte-13eo3pq">← Tilbake</a> <header class="person-header svelte-13eo3pq"><div class="header-content svelte-13eo3pq">`);
          if (person.image_url) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<div class="person-portrait svelte-13eo3pq"><img${attr("src", person.image_url)}${attr("alt", person.name)} class="svelte-13eo3pq"/></div>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> <div class="header-text svelte-13eo3pq"><h1 class="svelte-13eo3pq">${escape_html(person.name)}</h1> `);
          if (person.birth_year || person.death_year) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<p class="years svelte-13eo3pq">${escape_html(person.birth_year || "?")}–${escape_html(person.death_year || "")}</p>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (allRoles.length > 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<div class="all-roles svelte-13eo3pq"><!--[-->`);
            const each_array = ensure_array_like(allRoles);
            for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
              let roleSummary = each_array[$$index];
              $$renderer2.push(`<span${attr_class("role-pill svelte-13eo3pq", void 0, {
                "creator": ["playwright", "composer", "librettist"].includes(roleSummary.role)
              })}>${escape_html(roleSummary.label)} <span class="role-count svelte-13eo3pq">${escape_html(roleSummary.count)}</span></span>`);
            }
            $$renderer2.push(`<!--]--></div>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (person.bio) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<p class="bio svelte-13eo3pq">${escape_html(person.bio)}</p>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> <div class="external-links svelte-13eo3pq">`);
          if (person.sceneweb_url) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<a${attr("href", person.sceneweb_url)} target="_blank" rel="noopener" class="external-link svelte-13eo3pq">Sceneweb</a>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (person.wikipedia_url) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<a${attr("href", person.wikipedia_url)} target="_blank" rel="noopener" class="external-link svelte-13eo3pq">Wikipedia</a>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (person.bokselskap_url) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<a${attr("href", person.bokselskap_url)} target="_blank" rel="noopener" class="external-link svelte-13eo3pq">Bokselskap</a>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--></div></div></div></header> `);
          if (worksWritten.length > 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<section class="works-section svelte-13eo3pq"><h2 class="svelte-13eo3pq">Stykker av ${escape_html(person.name)} (${escape_html(worksWritten.length)})</h2> <div class="works-grid svelte-13eo3pq"><!--[-->`);
            const each_array_1 = ensure_array_like(worksWritten);
            for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
              let work = each_array_1[$$index_1];
              $$renderer2.push(`<a${attr("href", `/verk/${stringify(work.id)}`)} class="work-card svelte-13eo3pq"><div class="work-image svelte-13eo3pq">`);
              if (work.image_url) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", getImageUrl(work.image_url))}${attr("alt", work.title)} loading="lazy" class="svelte-13eo3pq"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="work-placeholder svelte-13eo3pq">Teater</div>`);
              }
              $$renderer2.push(`<!--]--></div> <div class="work-info svelte-13eo3pq"><h3 class="svelte-13eo3pq">${escape_html(work.title)}</h3> <div class="work-meta svelte-13eo3pq">`);
              if (work.year_written) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="work-year svelte-13eo3pq">${escape_html(work.year_written)}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (work.performance_count > 0) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="work-count svelte-13eo3pq">${escape_html(work.performance_count)} opptak</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div></div></a>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (worksComposed.length > 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<section class="works-section svelte-13eo3pq"><h2 class="svelte-13eo3pq">Komponert (${escape_html(worksComposed.length)})</h2> <div class="works-grid svelte-13eo3pq"><!--[-->`);
            const each_array_2 = ensure_array_like(worksComposed);
            for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
              let work = each_array_2[$$index_2];
              $$renderer2.push(`<a${attr("href", `/verk/${stringify(work.id)}`)} class="work-card svelte-13eo3pq"><div class="work-image svelte-13eo3pq">`);
              if (work.image_url) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", getImageUrl(work.image_url))}${attr("alt", work.title)} loading="lazy" class="svelte-13eo3pq"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="work-placeholder svelte-13eo3pq">Musikk</div>`);
              }
              $$renderer2.push(`<!--]--></div> <div class="work-info svelte-13eo3pq"><h3 class="svelte-13eo3pq">${escape_html(work.title)}</h3> <div class="work-meta svelte-13eo3pq">`);
              if (work.composer_role && work.composer_role !== "composer") {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="composer-role svelte-13eo3pq">${escape_html(getComposerRoleLabel(work.composer_role))}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (work.year_written) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="work-year svelte-13eo3pq">${escape_html(work.year_written)}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (work.performance_count > 0) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="work-count svelte-13eo3pq">${escape_html(work.performance_count)} opptak</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div></div></a>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (librettos.length > 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<section class="works-section svelte-13eo3pq"><h2 class="svelte-13eo3pq">Librettoer (${escape_html(librettos.length)})</h2> <div class="works-grid svelte-13eo3pq"><!--[-->`);
            const each_array_3 = ensure_array_like(librettos);
            for (let $$index_3 = 0, $$length = each_array_3.length; $$index_3 < $$length; $$index_3++) {
              let work = each_array_3[$$index_3];
              $$renderer2.push(`<a${attr("href", `/verk/${stringify(work.id)}`)} class="work-card svelte-13eo3pq"><div class="work-image svelte-13eo3pq">`);
              if (work.image_url) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", getImageUrl(work.image_url))}${attr("alt", work.title)} loading="lazy" class="svelte-13eo3pq"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="work-placeholder svelte-13eo3pq">Opera</div>`);
              }
              $$renderer2.push(`<!--]--></div> <div class="work-info svelte-13eo3pq"><h3 class="svelte-13eo3pq">${escape_html(work.title)}</h3> <div class="work-meta svelte-13eo3pq">`);
              if (work.year_written) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="work-year svelte-13eo3pq">${escape_html(work.year_written)}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (work.performance_count > 0) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="work-count svelte-13eo3pq">${escape_html(work.performance_count)} opptak</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div></div></a>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (performancesAbout.length > 0 || episodesAbout.length > 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<section class="nrk-about svelte-13eo3pq"><h2 class="svelte-13eo3pq">Programmer om ${escape_html(person.name)}</h2> <div class="about-grid svelte-13eo3pq"><!--[-->`);
            const each_array_4 = ensure_array_like(performancesAbout);
            for (let $$index_4 = 0, $$length = each_array_4.length; $$index_4 < $$length; $$index_4++) {
              let perf = each_array_4[$$index_4];
              $$renderer2.push(`<a${attr("href", `/opptak/${stringify(perf.id)}`)} class="about-card svelte-13eo3pq"><div class="about-image svelte-13eo3pq">`);
              if (perf.image_url) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", getImageUrl(perf.image_url))}${attr("alt", perf.title)} loading="lazy" class="svelte-13eo3pq"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="about-placeholder svelte-13eo3pq">${escape_html(perf.medium === "radio" ? "Radio" : "TV")}</div>`);
              }
              $$renderer2.push(`<!--]--></div> <div class="about-info svelte-13eo3pq"><h3 class="svelte-13eo3pq">${escape_html(perf.title)}</h3> <div class="about-meta svelte-13eo3pq">`);
              if (perf.episode_count > 1) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="about-badge svelte-13eo3pq">${escape_html(perf.episode_count)} episoder</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (perf.total_duration) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="about-duration svelte-13eo3pq">${escape_html(formatDuration(perf.total_duration))}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (perf.medium) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span${attr_class("medium-badge svelte-13eo3pq", void 0, { "radio": perf.medium === "radio" })}>${escape_html(perf.medium === "radio" ? "Radio" : "TV")}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div></div></a>`);
            }
            $$renderer2.push(`<!--]--> <!--[-->`);
            const each_array_5 = ensure_array_like(episodesAbout);
            for (let $$index_5 = 0, $$length = each_array_5.length; $$index_5 < $$length; $$index_5++) {
              let ep = each_array_5[$$index_5];
              $$renderer2.push(`<a${attr("href", ep.performance_id ? `/opptak/${ep.performance_id}` : `/episode/${ep.prf_id}`)} class="about-card svelte-13eo3pq"><div class="about-image svelte-13eo3pq">`);
              if (ep.image_url) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", getImageUrl(ep.image_url))}${attr("alt", ep.title)} loading="lazy" class="svelte-13eo3pq"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="about-placeholder svelte-13eo3pq">${escape_html(ep.medium === "radio" ? "Radio" : "TV")}</div>`);
              }
              $$renderer2.push(`<!--]--></div> <div class="about-info svelte-13eo3pq"><h3 class="svelte-13eo3pq">${escape_html(ep.title)}</h3> <div class="about-meta svelte-13eo3pq">`);
              if (ep.perf_title) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="about-badge svelte-13eo3pq">${escape_html(ep.perf_title)}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (ep.duration_seconds) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="about-duration svelte-13eo3pq">${escape_html(formatDuration(ep.duration_seconds))}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (ep.medium) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span${attr_class("medium-badge svelte-13eo3pq", void 0, { "radio": ep.medium === "radio" })}>${escape_html(ep.medium === "radio" ? "Radio" : "TV")}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div></div></a>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> `);
          if (nrkAboutPrograms.length > 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<section class="nrk-about svelte-13eo3pq"><h2 class="svelte-13eo3pq">Om ${escape_html(person.name)} i NRK-arkivet</h2> <div class="about-grid svelte-13eo3pq"><!--[-->`);
            const each_array_6 = ensure_array_like(nrkAboutPrograms);
            for (let $$index_6 = 0, $$length = each_array_6.length; $$index_6 < $$length; $$index_6++) {
              let program = each_array_6[$$index_6];
              $$renderer2.push(`<a${attr("href", program.nrk_url)} target="_blank" rel="noopener" class="about-card svelte-13eo3pq"><div class="about-image svelte-13eo3pq">`);
              if (program.image_url) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", program.image_url)}${attr("alt", program.title)} loading="lazy" class="svelte-13eo3pq"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="about-placeholder svelte-13eo3pq">NRK</div>`);
              }
              $$renderer2.push(`<!--]--></div> <div class="about-info svelte-13eo3pq"><h3 class="svelte-13eo3pq">${escape_html(program.title)}</h3> <div class="about-meta svelte-13eo3pq">`);
              if (program.program_type === "serie") {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="about-badge svelte-13eo3pq">Serie (${escape_html(program.episode_count)} ep)</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (program.duration_seconds) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="about-duration svelte-13eo3pq">${escape_html(formatDuration(program.duration_seconds))}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div></div></a>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          } else {
            $$renderer2.push("<!--[!-->");
          }
          $$renderer2.push(`<!--]--> <!--[-->`);
          const each_array_7 = ensure_array_like(performancesByRole);
          for (let $$index_8 = 0, $$length = each_array_7.length; $$index_8 < $$length; $$index_8++) {
            let group = each_array_7[$$index_8];
            $$renderer2.push(`<section class="role-section svelte-13eo3pq"><h2 class="svelte-13eo3pq">${escape_html(getRoleLabel(group.role))} (${escape_html(group.performances.length)})</h2> <div class="performances-grid svelte-13eo3pq"><!--[-->`);
            const each_array_8 = ensure_array_like(group.performances);
            for (let $$index_7 = 0, $$length2 = each_array_8.length; $$index_7 < $$length2; $$index_7++) {
              let perf = each_array_8[$$index_7];
              $$renderer2.push(`<a${attr("href", `/opptak/${stringify(perf.id)}`)} class="perf-card svelte-13eo3pq"><div class="perf-image svelte-13eo3pq">`);
              if (perf.image_url) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<img${attr("src", getImageUrl(perf.image_url))}${attr("alt", perf.work_title)} loading="lazy" class="svelte-13eo3pq"/>`);
              } else {
                $$renderer2.push("<!--[!-->");
                $$renderer2.push(`<div class="perf-placeholder svelte-13eo3pq">Teater</div>`);
              }
              $$renderer2.push(`<!--]--></div> <div class="perf-info svelte-13eo3pq"><h3 class="svelte-13eo3pq">${escape_html(perf.work_title)}</h3> `);
              if (perf.character_name) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="character svelte-13eo3pq">som ${escape_html(perf.character_name)}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> <div class="perf-meta svelte-13eo3pq">`);
              if (perf.year) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="perf-year svelte-13eo3pq">${escape_html(perf.year)}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--> `);
              if (perf.playwright_name) {
                $$renderer2.push("<!--[-->");
                $$renderer2.push(`<span class="playwright svelte-13eo3pq">${escape_html(perf.playwright_name)}</span>`);
              } else {
                $$renderer2.push("<!--[!-->");
              }
              $$renderer2.push(`<!--]--></div></div></a>`);
            }
            $$renderer2.push(`<!--]--></div></section>`);
          }
          $$renderer2.push(`<!--]--> `);
          if (allRoles.length === 0 && nrkAboutPrograms.length === 0) {
            $$renderer2.push("<!--[-->");
            $$renderer2.push(`<div class="no-content svelte-13eo3pq"><p>Ingen opptak registrert for denne personen ennå.</p></div>`);
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
