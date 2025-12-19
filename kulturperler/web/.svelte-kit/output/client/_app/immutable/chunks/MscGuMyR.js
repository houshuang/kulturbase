let d=null;async function m(){return d||E()}async function E(){const p=await(window.initSqlJs||await u())({locateFile:i=>`https://sql.js.org/dist/${i}`}),s=await(await fetch("/kulturperler.db")).arrayBuffer();return d=new p.Database(new Uint8Array(s)),d}async function u(){return new Promise((r,p)=>{const e=document.createElement("script");e.src="https://sql.js.org/dist/sql-wasm.js",e.onload=()=>r(window.initSqlJs),e.onerror=p,document.head.appendChild(e)})}function n(){if(!d)throw new Error("Database not initialized");return d}function f(r){const e=n().prepare(`
		SELECT
			e.*,
			p.title as play_title,
			playwright.name as playwright_name
		FROM episodes e
		LEFT JOIN plays p ON e.play_id = p.id
		LEFT JOIN persons playwright ON p.playwright_id = playwright.id
		WHERE e.prf_id = ?
	`);e.bind([r]);let t=null;return e.step()&&(t=e.getAsObject()),e.free(),t}function O(r){const e=n().prepare(`
		SELECT ep.*, p.name as person_name
		FROM episode_persons ep
		JOIN persons p ON ep.person_id = p.id
		WHERE ep.episode_id = ?
		ORDER BY
			CASE ep.role
				WHEN 'director' THEN 1
				WHEN 'playwright' THEN 2
				WHEN 'actor' THEN 3
				ELSE 4
			END,
			p.name
	`);e.bind([r]);const t=[];for(;e.step();)t.push(e.getAsObject());return e.free(),t}function h(r){const e=n().prepare("SELECT * FROM persons WHERE id = ?");e.bind([r]);let t=null;return e.step()&&(t=e.getAsObject()),e.free(),t}function R(r){const e=n().prepare(`
		SELECT DISTINCT p.*
		FROM persons p
		JOIN episode_persons ep ON p.id = ep.person_id
		WHERE ep.role = ?
		ORDER BY p.name
	`);e.bind([r]);const t=[];for(;e.step();)t.push(e.getAsObject());return e.free(),t}function y(r){const e=n().prepare(`
		SELECT p.*, playwright.name as playwright_name
		FROM plays p
		LEFT JOIN persons playwright ON p.playwright_id = playwright.id
		WHERE p.id = ?
	`);e.bind([r]);let t=null;return e.step()&&(t=e.getAsObject()),e.free(),t}function T(){const p=n().prepare(`
		SELECT
			p.id,
			p.name,
			COUNT(DISTINCT e.prf_id) as episode_count,
			COUNT(DISTINCT pl.id) as play_count
		FROM persons p
		JOIN plays pl ON p.id = pl.playwright_id
		JOIN episodes e ON pl.id = e.play_id
		GROUP BY p.id
		HAVING episode_count > 0
		ORDER BY episode_count DESC, p.name
	`),e=[];for(;p.step();)e.push(p.getAsObject());return p.free(),e}function _(r){const p=n(),e=`%${r}%`,t=p.prepare(`
		SELECT p.*, COUNT(DISTINCT pl.id) as play_count
		FROM persons p
		JOIN plays pl ON p.id = pl.playwright_id
		WHERE p.name LIKE ? OR p.normalized_name LIKE ?
		GROUP BY p.id
		HAVING play_count > 0
		ORDER BY play_count DESC
		LIMIT 5
	`);t.bind([e,e]);const s=[];for(;t.step();)s.push(t.getAsObject());return t.free(),s}function N(){const p=n().prepare("SELECT MIN(year) as min, MAX(year) as max FROM episodes WHERE year IS NOT NULL");p.step();const e=p.getAsObject();return p.free(),e}function g(r){const e=n().prepare(`
		SELECT * FROM play_external_links WHERE play_id = ?
		ORDER BY title
	`);e.bind([r]);const t=[];for(;e.step();)t.push(e.getAsObject());return e.free(),t}function w(r){const e=n().prepare(`
		SELECT
			perf.*,
			w.title as work_title,
			w.playwright_id,
			playwright.name as playwright_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		LEFT JOIN plays w ON perf.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		WHERE perf.id = ?
	`);e.bind([r]);let t=null;return e.step()&&(t=e.getAsObject()),e.free(),t}function b(r,p=50,e=0){const t=n();let s=`
		SELECT
			perf.*,
			w.title as work_title,
			w.playwright_id,
			playwright.name as playwright_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		LEFT JOIN plays w ON perf.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
	`;const i=[],a=[];if(r.query){i.push("(perf.title LIKE ? OR perf.description LIKE ? OR w.title LIKE ?)");const c=`%${r.query}%`;a.push(c,c,c)}if(r.yearFrom&&(i.push("perf.year >= ?"),a.push(r.yearFrom)),r.yearTo&&(i.push("perf.year <= ?"),a.push(r.yearTo)),r.playwrightId&&(i.push("w.playwright_id = ?"),a.push(r.playwrightId)),r.directorId&&(i.push(`EXISTS (
			SELECT 1 FROM performance_persons pp
			WHERE pp.performance_id = perf.id
			AND pp.person_id = ?
			AND pp.role = 'director'
		)`),a.push(r.directorId)),r.actorId&&(i.push(`EXISTS (
			SELECT 1 FROM performance_persons pp
			WHERE pp.performance_id = perf.id
			AND pp.person_id = ?
			AND pp.role = 'actor'
		)`),a.push(r.actorId)),r.mediums&&r.mediums.length>0&&r.mediums.length<2){const c=r.mediums.map(()=>"?").join(",");i.push(`perf.medium IN (${c})`),a.push(...r.mediums)}i.length>0&&(s+=` WHERE ${i.join(" AND ")}`),s+=" ORDER BY perf.year DESC, perf.title ASC LIMIT ? OFFSET ?",a.push(p,e);const o=t.prepare(s);o.bind(a);const l=[];for(;o.step();)l.push(o.getAsObject());return o.free(),l}function I(r){const p=n();let e="SELECT COUNT(*) as count FROM performances perf";const t=[],s=[];if(r?.query){e+=" LEFT JOIN plays w ON perf.work_id = w.id",t.push("(perf.title LIKE ? OR perf.description LIKE ? OR w.title LIKE ?)");const o=`%${r.query}%`;s.push(o,o,o)}if(r?.yearFrom&&(t.push("perf.year >= ?"),s.push(r.yearFrom)),r?.yearTo&&(t.push("perf.year <= ?"),s.push(r.yearTo)),r?.mediums&&r.mediums.length>0&&r.mediums.length<2){const o=r.mediums.map(()=>"?").join(",");t.push(`perf.medium IN (${o})`),s.push(...r.mediums)}t.length>0&&(e+=` WHERE ${t.join(" AND ")}`);const i=p.prepare(e);i.bind(s),i.step();const a=i.getAsObject();return i.free(),a.count}function C(r){const e=n().prepare(`
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
	`);e.bind([r]);const t=[];for(;e.step();)t.push(e.getAsObject());return e.free(),t}function S(r){const e=n().prepare(`
		SELECT *
		FROM episodes
		WHERE performance_id = ?
		ORDER BY prf_id ASC
	`);e.bind([r]);const t=[];for(;e.step();)t.push(e.getAsObject());return e.free(),t}function L(r,p){const t=n().prepare(`
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
	`);t.bind([r,p]);const s=[];for(;t.step();)s.push(t.getAsObject());return t.free(),s}function A(r,p){const t=n().prepare(`
		SELECT
			perf.*,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		WHERE perf.work_id = ? AND perf.medium = ?
		ORDER BY perf.year DESC
	`);t.bind([r,p]);const s=[];for(;t.step();)s.push(t.getAsObject());return t.free(),s}function F(){const p=n().prepare(`
		SELECT medium, COUNT(*) as count
		FROM performances
		GROUP BY medium
	`),e={tv:0,radio:0};for(;p.step();){const t=p.getAsObject();t.medium==="tv"?e.tv=t.count:t.medium==="radio"&&(e.radio=t.count)}return p.free(),e}function M(r){const e=n().prepare(`
		SELECT * FROM nrk_about_programs
		WHERE person_id = ?
		ORDER BY interest_score DESC
		LIMIT 10
	`);e.bind([r]);const t=[];for(;e.step();)t.push(e.getAsObject());return e.free(),t}function D(){const p=n().prepare(`
		SELECT
			p.id,
			p.name,
			p.birth_year,
			p.death_year,
			p.nationality,
			COUNT(DISTINCT pl.id) as play_count,
			COUNT(DISTINCT perf.id) as performance_count
		FROM persons p
		JOIN plays pl ON p.id = pl.playwright_id
		JOIN performances perf ON perf.work_id = pl.id
		GROUP BY p.id
		HAVING play_count > 0
		ORDER BY p.name
	`),e=[];for(;p.step();)e.push(p.getAsObject());return p.free(),e}function H(){const p=n().prepare(`
		SELECT DISTINCT p.nationality
		FROM persons p
		JOIN plays pl ON p.id = pl.playwright_id
		WHERE p.nationality IS NOT NULL AND p.nationality != ''
		ORDER BY p.nationality
	`),e=[];for(;p.step();){const t=p.getAsObject();e.push(t.nationality)}return p.free(),e}function W(r="title"){const p=n();let e="pl.title ASC";r==="year"&&(e="pl.year_written DESC NULLS LAST, pl.title ASC"),r==="playwright"&&(e="playwright.name ASC NULLS LAST, pl.title ASC");const t=p.prepare(`
		SELECT
			pl.id,
			pl.title,
			pl.original_title,
			pl.year_written,
			pl.playwright_id,
			playwright.name as playwright_name,
			COUNT(DISTINCT perf.id) as performance_count
		FROM plays pl
		LEFT JOIN persons playwright ON pl.playwright_id = playwright.id
		LEFT JOIN performances perf ON perf.work_id = pl.id
		GROUP BY pl.id
		HAVING performance_count > 0
		ORDER BY ${e}
	`),s=[];for(;t.step();)s.push(t.getAsObject());return t.free(),s}function j(){const p=n().prepare(`
		SELECT COUNT(DISTINCT pl.id) as count
		FROM plays pl
		JOIN performances perf ON perf.work_id = pl.id
	`);p.step();const e=p.getAsObject();return p.free(),e.count}function J(){const p=n().prepare(`
		SELECT COUNT(DISTINCT p.id) as count
		FROM persons p
		JOIN plays pl ON p.id = pl.playwright_id
		JOIN performances perf ON perf.work_id = pl.id
	`);p.step();const e=p.getAsObject();return p.free(),e.count}export{R as a,T as b,F as c,j as d,J as e,W as f,N as g,D as h,b as i,I as j,f as k,O as l,w as m,C as n,S as o,y as p,L as q,h as r,_ as s,n as t,M as u,H as v,A as w,g as x,m as y};
