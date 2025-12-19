import type { Database, SqlJsStatic } from 'sql.js';
import type { Episode, Person, Play, Tag, EpisodeWithDetails, SearchFilters, EpisodePerson, PlayExternalLink, Performance, PerformanceWithDetails, PerformancePerson, NrkAboutProgram } from './types';

let db: Database | null = null;

export async function initDatabase(): Promise<Database> {
	if (db) return db;
	return loadDatabase();
}

export async function reloadDatabase(): Promise<Database> {
	db = null;
	return loadDatabase();
}

async function loadDatabase(): Promise<Database> {

	// Load sql.js via script tag (it doesn't support ES modules well)
	const initSqlJs = (window as any).initSqlJs || await loadSqlJs();

	const SQL: SqlJsStatic = await initSqlJs({
		locateFile: (file: string) => `https://sql.js.org/dist/${file}`
	});

	// Add timestamp to bust cache in development
	const cacheBuster = import.meta.env.DEV ? `?t=${Date.now()}` : '';
	const response = await fetch(`/kulturperler.db${cacheBuster}`);
	const buffer = await response.arrayBuffer();
	db = new SQL.Database(new Uint8Array(buffer));

	return db;
}

async function loadSqlJs(): Promise<any> {
	return new Promise((resolve, reject) => {
		const script = document.createElement('script');
		script.src = 'https://sql.js.org/dist/sql-wasm.js';
		script.onload = () => resolve((window as any).initSqlJs);
		script.onerror = reject;
		document.head.appendChild(script);
	});
}

export function getDatabase(): Database {
	if (!db) throw new Error('Database not initialized');
	return db;
}

export function searchEpisodes(filters: SearchFilters, limit = 50, offset = 0): EpisodeWithDetails[] {
	const db = getDatabase();

	let sql = `
		SELECT DISTINCT
			e.prf_id,
			e.title,
			e.description,
			e.year,
			e.duration_seconds,
			e.image_url,
			e.nrk_url,
			e.play_id,
			e.source,
			p.title as play_title,
			playwright.name as playwright_name,
			director.name as director_name
		FROM episodes e
		LEFT JOIN plays p ON e.play_id = p.id
		LEFT JOIN persons playwright ON p.playwright_id = playwright.id
		LEFT JOIN episode_persons ep_dir ON e.prf_id = ep_dir.episode_id AND ep_dir.role = 'director'
		LEFT JOIN persons director ON ep_dir.person_id = director.id
	`;

	const conditions: string[] = [];
	const params: (string | number)[] = [];

	if (filters.query) {
		conditions.push(`(e.title LIKE ? OR e.description LIKE ?)`);
		const term = `%${filters.query}%`;
		params.push(term, term);
	}

	if (filters.yearFrom) {
		conditions.push(`e.year >= ?`);
		params.push(filters.yearFrom);
	}

	if (filters.yearTo) {
		conditions.push(`e.year <= ?`);
		params.push(filters.yearTo);
	}

	if (filters.playwrightId) {
		conditions.push(`p.playwright_id = ?`);
		params.push(filters.playwrightId);
	}

	if (filters.directorId) {
		conditions.push(`EXISTS (
			SELECT 1 FROM episode_persons ep
			WHERE ep.episode_id = e.prf_id
			AND ep.person_id = ?
			AND ep.role = 'director'
		)`);
		params.push(filters.directorId);
	}

	if (filters.actorId) {
		conditions.push(`EXISTS (
			SELECT 1 FROM episode_persons ep
			WHERE ep.episode_id = e.prf_id
			AND ep.person_id = ?
			AND ep.role = 'actor'
		)`);
		params.push(filters.actorId);
	}

	if (filters.tagIds && filters.tagIds.length > 0) {
		const placeholders = filters.tagIds.map(() => '?').join(',');
		conditions.push(`EXISTS (
			SELECT 1 FROM episode_tags et
			WHERE et.episode_id = e.prf_id
			AND et.tag_id IN (${placeholders})
		)`);
		params.push(...filters.tagIds);
	}

	if (conditions.length > 0) {
		sql += ` WHERE ${conditions.join(' AND ')}`;
	}

	sql += ` ORDER BY e.year DESC, e.title ASC LIMIT ? OFFSET ?`;
	params.push(limit, offset);

	const stmt = db.prepare(sql);
	stmt.bind(params);

	const results: EpisodeWithDetails[] = [];
	while (stmt.step()) {
		const row = stmt.getAsObject() as unknown as EpisodeWithDetails;
		results.push(row);
	}
	stmt.free();

	return results;
}

export function getEpisode(prfId: string): EpisodeWithDetails | null {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			e.*,
			p.title as play_title,
			playwright.name as playwright_name
		FROM episodes e
		LEFT JOIN plays p ON e.play_id = p.id
		LEFT JOIN persons playwright ON p.playwright_id = playwright.id
		WHERE e.prf_id = ?
	`);
	stmt.bind([prfId]);

	let result: EpisodeWithDetails | null = null;
	if (stmt.step()) {
		result = stmt.getAsObject() as unknown as EpisodeWithDetails;
	}
	stmt.free();

	return result;
}

export function getEpisodeContributors(prfId: string): (EpisodePerson & { person_name: string })[] {
	const db = getDatabase();

	const stmt = db.prepare(`
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
	`);
	stmt.bind([prfId]);

	const results: (EpisodePerson & { person_name: string })[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as EpisodePerson & { person_name: string });
	}
	stmt.free();

	return results;
}

export function getPerson(id: number): Person | null {
	const db = getDatabase();
	const stmt = db.prepare('SELECT * FROM persons WHERE id = ?');
	stmt.bind([id]);

	let result: Person | null = null;
	if (stmt.step()) {
		result = stmt.getAsObject() as unknown as Person;
	}
	stmt.free();

	return result;
}

export function searchPersons(query: string, role?: string, limit = 20): Person[] {
	const db = getDatabase();

	let sql = `
		SELECT DISTINCT p.*
		FROM persons p
	`;

	const params: (string | number)[] = [];

	if (role) {
		sql += ` JOIN episode_persons ep ON p.id = ep.person_id AND ep.role = ?`;
		params.push(role);
	}

	sql += ` WHERE p.name LIKE ? OR p.normalized_name LIKE ?`;
	const term = `%${query}%`;
	params.push(term, term);

	sql += ` ORDER BY p.name LIMIT ?`;
	params.push(limit);

	const stmt = db.prepare(sql);
	stmt.bind(params);

	const results: Person[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as Person);
	}
	stmt.free();

	return results;
}

export function getPersonsByRole(role: string): Person[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT DISTINCT p.*
		FROM persons p
		JOIN episode_persons ep ON p.id = ep.person_id
		WHERE ep.role = ?
		ORDER BY p.name
	`);
	stmt.bind([role]);

	const results: Person[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as Person);
	}
	stmt.free();

	return results;
}

export function getPlay(id: number): (Play & { playwright_name?: string }) | null {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT p.*, playwright.name as playwright_name
		FROM plays p
		LEFT JOIN persons playwright ON p.playwright_id = playwright.id
		WHERE p.id = ?
	`);
	stmt.bind([id]);

	let result: (Play & { playwright_name?: string }) | null = null;
	if (stmt.step()) {
		result = stmt.getAsObject() as unknown as Play & { playwright_name?: string };
	}
	stmt.free();

	return result;
}

export function getTags(): Tag[] {
	const db = getDatabase();
	const stmt = db.prepare('SELECT * FROM tags ORDER BY display_name');

	const results: Tag[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as Tag);
	}
	stmt.free();

	return results;
}

export interface PlaywrightWithCount {
	id: number;
	name: string;
	episode_count: number;
	play_count: number;
}

export function getPlaywrightsWithCounts(): PlaywrightWithCount[] {
	const db = getDatabase();
	const stmt = db.prepare(`
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
	`);

	const results: PlaywrightWithCount[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PlaywrightWithCount);
	}
	stmt.free();

	return results;
}

export function searchAuthors(query: string): (Person & { play_count?: number })[] {
	const db = getDatabase();
	const term = `%${query}%`;

	const stmt = db.prepare(`
		SELECT p.*, COUNT(DISTINCT pl.id) as play_count
		FROM persons p
		JOIN plays pl ON p.id = pl.playwright_id
		WHERE p.name LIKE ? OR p.normalized_name LIKE ?
		GROUP BY p.id
		HAVING play_count > 0
		ORDER BY play_count DESC
		LIMIT 5
	`);
	stmt.bind([term, term]);

	const results: (Person & { play_count?: number })[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as Person & { play_count?: number });
	}
	stmt.free();

	return results;
}

export function getYearRange(): { min: number; max: number } {
	const db = getDatabase();
	const stmt = db.prepare('SELECT MIN(year) as min, MAX(year) as max FROM episodes WHERE year IS NOT NULL');
	stmt.step();
	const result = stmt.getAsObject() as { min: number; max: number };
	stmt.free();
	return result;
}

export function getEpisodeCount(filters?: SearchFilters): number {
	const db = getDatabase();

	let sql = 'SELECT COUNT(DISTINCT e.prf_id) as count FROM episodes e';
	const conditions: string[] = [];
	const params: (string | number)[] = [];

	if (filters?.query) {
		conditions.push(`(e.title LIKE ? OR e.description LIKE ?)`);
		const term = `%${filters.query}%`;
		params.push(term, term);
	}

	if (filters?.yearFrom) {
		conditions.push(`e.year >= ?`);
		params.push(filters.yearFrom);
	}

	if (filters?.yearTo) {
		conditions.push(`e.year <= ?`);
		params.push(filters.yearTo);
	}

	if (conditions.length > 0) {
		sql += ` WHERE ${conditions.join(' AND ')}`;
	}

	const stmt = db.prepare(sql);
	stmt.bind(params);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();

	return result.count;
}

export function getPlayExternalLinks(playId: number): PlayExternalLink[] {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT * FROM play_external_links WHERE play_id = ?
		ORDER BY title
	`);
	stmt.bind([playId]);

	const results: PlayExternalLink[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PlayExternalLink);
	}
	stmt.free();

	return results;
}

// ===== Performance-related queries =====

export function getPerformance(id: number): PerformanceWithDetails | null {
	const db = getDatabase();

	const stmt = db.prepare(`
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
	`);
	stmt.bind([id]);

	let result: PerformanceWithDetails | null = null;
	if (stmt.step()) {
		result = stmt.getAsObject() as unknown as PerformanceWithDetails;
	}
	stmt.free();

	return result;
}

export function searchPerformances(filters: SearchFilters, limit = 50, offset = 0): PerformanceWithDetails[] {
	const db = getDatabase();

	let sql = `
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
	`;

	const conditions: string[] = [];
	const params: (string | number)[] = [];

	if (filters.query) {
		conditions.push(`(perf.title LIKE ? OR perf.description LIKE ? OR w.title LIKE ?)`);
		const term = `%${filters.query}%`;
		params.push(term, term, term);
	}

	if (filters.yearFrom) {
		conditions.push(`perf.year >= ?`);
		params.push(filters.yearFrom);
	}

	if (filters.yearTo) {
		conditions.push(`perf.year <= ?`);
		params.push(filters.yearTo);
	}

	if (filters.playwrightId) {
		conditions.push(`w.playwright_id = ?`);
		params.push(filters.playwrightId);
	}

	if (filters.directorId) {
		conditions.push(`EXISTS (
			SELECT 1 FROM performance_persons pp
			WHERE pp.performance_id = perf.id
			AND pp.person_id = ?
			AND pp.role = 'director'
		)`);
		params.push(filters.directorId);
	}

	if (filters.actorId) {
		conditions.push(`EXISTS (
			SELECT 1 FROM performance_persons pp
			WHERE pp.performance_id = perf.id
			AND pp.person_id = ?
			AND pp.role = 'actor'
		)`);
		params.push(filters.actorId);
	}

	// Medium filter (tv/radio)
	if (filters.mediums && filters.mediums.length > 0 && filters.mediums.length < 2) {
		const placeholders = filters.mediums.map(() => '?').join(',');
		conditions.push(`perf.medium IN (${placeholders})`);
		params.push(...filters.mediums);
	}

	if (conditions.length > 0) {
		sql += ` WHERE ${conditions.join(' AND ')}`;
	}

	sql += ` ORDER BY perf.year DESC, perf.title ASC LIMIT ? OFFSET ?`;
	params.push(limit, offset);

	const stmt = db.prepare(sql);
	stmt.bind(params);

	const results: PerformanceWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PerformanceWithDetails);
	}
	stmt.free();

	return results;
}

export function getPerformanceCount(filters?: SearchFilters): number {
	const db = getDatabase();

	let sql = `SELECT COUNT(*) as count FROM performances perf`;
	const conditions: string[] = [];
	const params: (string | number)[] = [];

	if (filters?.query) {
		sql += ` LEFT JOIN plays w ON perf.work_id = w.id`;
		conditions.push(`(perf.title LIKE ? OR perf.description LIKE ? OR w.title LIKE ?)`);
		const term = `%${filters.query}%`;
		params.push(term, term, term);
	}

	if (filters?.yearFrom) {
		conditions.push(`perf.year >= ?`);
		params.push(filters.yearFrom);
	}

	if (filters?.yearTo) {
		conditions.push(`perf.year <= ?`);
		params.push(filters.yearTo);
	}

	// Medium filter (tv/radio)
	if (filters?.mediums && filters.mediums.length > 0 && filters.mediums.length < 2) {
		const placeholders = filters.mediums.map(() => '?').join(',');
		conditions.push(`perf.medium IN (${placeholders})`);
		params.push(...filters.mediums);
	}

	if (conditions.length > 0) {
		sql += ` WHERE ${conditions.join(' AND ')}`;
	}

	const stmt = db.prepare(sql);
	stmt.bind(params);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();

	return result.count;
}

export function getPerformanceContributors(performanceId: number): (PerformancePerson & { person_name: string })[] {
	const db = getDatabase();

	const stmt = db.prepare(`
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

	const results: (PerformancePerson & { person_name: string })[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PerformancePerson & { person_name: string });
	}
	stmt.free();

	return results;
}

export function getPerformanceMedia(performanceId: number): Episode[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT *
		FROM episodes
		WHERE performance_id = ?
		ORDER BY prf_id ASC
	`);
	stmt.bind([performanceId]);

	const results: Episode[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as Episode);
	}
	stmt.free();

	return results;
}

export function getOtherPerformances(workId: number, excludePerformanceId: number): PerformanceWithDetails[] {
	const db = getDatabase();

	const stmt = db.prepare(`
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

	const results: PerformanceWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PerformanceWithDetails);
	}
	stmt.free();

	return results;
}

export function getWorkPerformances(workId: number): PerformanceWithDetails[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			perf.*,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		WHERE perf.work_id = ?
		ORDER BY perf.year DESC
	`);
	stmt.bind([workId]);

	const results: PerformanceWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PerformanceWithDetails);
	}
	stmt.free();

	return results;
}

export function getWorkPerformancesByMedium(workId: number, medium: 'tv' | 'radio'): PerformanceWithDetails[] {
	const db = getDatabase();

	const stmt = db.prepare(`
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
	`);
	stmt.bind([workId, medium]);

	const results: PerformanceWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PerformanceWithDetails);
	}
	stmt.free();

	return results;
}

export function getMediumCounts(): { tv: number; radio: number } {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT medium, COUNT(*) as count
		FROM performances
		GROUP BY medium
	`);

	const result = { tv: 0, radio: 0 };
	while (stmt.step()) {
		const row = stmt.getAsObject() as { medium: string; count: number };
		if (row.medium === 'tv') result.tv = row.count;
		else if (row.medium === 'radio') result.radio = row.count;
	}
	stmt.free();

	return result;
}

export function getNrkAboutPrograms(personId: number): NrkAboutProgram[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT * FROM nrk_about_programs
		WHERE person_id = ?
		ORDER BY interest_score DESC
		LIMIT 10
	`);
	stmt.bind([personId]);

	const results: NrkAboutProgram[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as NrkAboutProgram);
	}
	stmt.free();

	return results;
}

export interface PlaywrightWithDetails {
	id: number;
	name: string;
	birth_year: number | null;
	death_year: number | null;
	nationality: string | null;
	play_count: number;
	performance_count: number;
}

export function getAllPlaywrights(): PlaywrightWithDetails[] {
	const db = getDatabase();
	const stmt = db.prepare(`
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
	`);

	const results: PlaywrightWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PlaywrightWithDetails);
	}
	stmt.free();

	return results;
}

export function getNationalities(): string[] {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT DISTINCT p.nationality
		FROM persons p
		JOIN plays pl ON p.id = pl.playwright_id
		WHERE p.nationality IS NOT NULL AND p.nationality != ''
		ORDER BY p.nationality
	`);

	const results: string[] = [];
	while (stmt.step()) {
		const row = stmt.getAsObject() as { nationality: string };
		results.push(row.nationality);
	}
	stmt.free();

	return results;
}

export interface PlayWithDetails {
	id: number;
	title: string;
	original_title: string | null;
	year_written: number | null;
	playwright_id: number | null;
	playwright_name: string | null;
	performance_count: number;
}

export function getAllPlays(sortBy: 'title' | 'year' | 'playwright' = 'title'): PlayWithDetails[] {
	const db = getDatabase();

	let orderBy = 'pl.title ASC';
	if (sortBy === 'year') orderBy = 'pl.year_written DESC NULLS LAST, pl.title ASC';
	if (sortBy === 'playwright') orderBy = 'playwright.name ASC NULLS LAST, pl.title ASC';

	const stmt = db.prepare(`
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
		ORDER BY ${orderBy}
	`);

	const results: PlayWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PlayWithDetails);
	}
	stmt.free();

	return results;
}

export function getPlayCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(DISTINCT pl.id) as count
		FROM plays pl
		JOIN performances perf ON perf.work_id = pl.id
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

export function getAuthorCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(DISTINCT p.id) as count
		FROM persons p
		JOIN plays pl ON p.id = pl.playwright_id
		JOIN performances perf ON perf.work_id = pl.id
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}
