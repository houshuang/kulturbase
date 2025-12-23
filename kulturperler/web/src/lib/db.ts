import type { Database, SqlJsStatic } from 'sql.js';
import type { Episode, Person, Work, Tag, EpisodeWithDetails, SearchFilters, EpisodePerson, WorkExternalLink, Performance, PerformanceWithDetails, PerformancePerson, NrkAboutProgram, WorkCategory, WorkType, Institution, ExternalResource, ExternalResourceFilters, WorkComposer, ComposerRole } from './types';

// Alias for backwards compatibility
type Play = Work;
type PlayExternalLink = WorkExternalLink;

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
			e.work_id,
			e.work_id as play_id,
			e.source,
			w.title as work_title,
			w.title as play_title,
			playwright.name as playwright_name,
			director.name as director_name
		FROM episodes e
		LEFT JOIN works w ON e.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
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
		conditions.push(`w.playwright_id = ?`);
		params.push(filters.playwrightId);
	}

	if (filters.category) {
		conditions.push(`w.category = ?`);
		params.push(filters.category);
	}

	if (filters.workType) {
		conditions.push(`w.work_type = ?`);
		params.push(filters.workType);
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
			e.work_id as play_id,
			w.title as work_title,
			w.title as play_title,
			playwright.name as playwright_name
		FROM episodes e
		LEFT JOIN works w ON e.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
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

export function getWork(id: number): (Work & { playwright_name?: string; composer_name?: string }) | null {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT w.*, playwright.name as playwright_name, composer.name as composer_name
		FROM works w
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		LEFT JOIN persons composer ON w.composer_id = composer.id
		WHERE w.id = ?
	`);
	stmt.bind([id]);

	let result: (Work & { playwright_name?: string; composer_name?: string }) | null = null;
	if (stmt.step()) {
		result = stmt.getAsObject() as unknown as Work & { playwright_name?: string; composer_name?: string };
	}
	stmt.free();

	return result;
}

// Alias for backwards compatibility
export const getPlay = getWork;

// Role labels for display (Norwegian)
const composerRoleLabels: Record<ComposerRole, string> = {
	composer: 'komp.',
	arranger: 'arr.',
	orchestrator: 'ork.',
	lyricist: 'tekst',
	adapter: 'bearb.'
};

export function getComposerRoleLabel(role: ComposerRole): string {
	return composerRoleLabels[role] || role;
}

export function getWorkComposers(workId: number): WorkComposer[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			wc.work_id,
			wc.person_id,
			wc.role,
			wc.sort_order,
			p.name as person_name,
			p.birth_year as person_birth_year,
			p.death_year as person_death_year
		FROM work_composers wc
		JOIN persons p ON wc.person_id = p.id
		WHERE wc.work_id = ?
		ORDER BY wc.sort_order, wc.role
	`);
	stmt.bind([workId]);

	const results: WorkComposer[] = [];
	while (stmt.step()) {
		const row = stmt.getAsObject();
		results.push({
			work_id: row.work_id as number,
			person_id: row.person_id as number,
			role: row.role as ComposerRole,
			sort_order: row.sort_order as number,
			person_name: row.person_name as string,
			person_birth_year: row.person_birth_year as number | null,
			person_death_year: row.person_death_year as number | null
		});
	}
	stmt.free();

	return results;
}

export function formatComposers(composers: WorkComposer[]): string {
	if (composers.length === 0) return '';

	return composers.map(c => {
		if (c.role === 'composer') {
			return c.person_name;
		}
		return `${c.person_name} (${getComposerRoleLabel(c.role as ComposerRole)})`;
	}).join(', ');
}

export interface WorkAsComposer extends Work {
	composer_role: ComposerRole;
}

export function getWorksAsComposer(personId: number): WorkAsComposer[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT w.*, wc.role as composer_role
		FROM works w
		JOIN work_composers wc ON w.id = wc.work_id
		WHERE wc.person_id = ?
		ORDER BY w.year_written DESC, w.title
	`);
	stmt.bind([personId]);

	const results: WorkAsComposer[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as WorkAsComposer);
	}
	stmt.free();

	return results;
}

export function getComposerWorkCount(personId: number): number {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT COUNT(DISTINCT work_id) as count
		FROM work_composers
		WHERE person_id = ?
	`);
	stmt.bind([personId]);

	let count = 0;
	if (stmt.step()) {
		const row = stmt.getAsObject() as { count: number };
		count = row.count;
	}
	stmt.free();

	return count;
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
			COUNT(DISTINCT w.id) as play_count
		FROM persons p
		JOIN works w ON p.id = w.playwright_id
		JOIN episodes e ON w.id = e.work_id
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
		SELECT p.*, COUNT(DISTINCT w.id) as play_count
		FROM persons p
		JOIN works w ON p.id = w.playwright_id
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

export function getWorkExternalLinks(workId: number): WorkExternalLink[] {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT * FROM work_external_links WHERE work_id = ?
		ORDER BY title
	`);
	stmt.bind([workId]);

	const results: WorkExternalLink[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as WorkExternalLink);
	}
	stmt.free();

	return results;
}

// Alias for backwards compatibility
export const getPlayExternalLinks = getWorkExternalLinks;

// ===== Performance-related queries =====

export function getPerformance(id: number): PerformanceWithDetails | null {
	const db = getDatabase();

	const stmt = db.prepare(`
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
			w.work_type,
			w.category,
			playwright.name as playwright_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		LEFT JOIN works w ON perf.work_id = w.id
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

	if (filters.category) {
		conditions.push(`w.category = ?`);
		params.push(filters.category);
	}

	if (filters.workType) {
		conditions.push(`w.work_type = ?`);
		params.push(filters.workType);
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

	// Always join works when we need category/workType or query filtering
	const needsWorksJoin = filters?.query || filters?.category || filters?.workType;
	let sql = `SELECT COUNT(*) as count FROM performances perf`;
	if (needsWorksJoin) {
		sql += ` LEFT JOIN works w ON perf.work_id = w.id`;
	}

	const conditions: string[] = [];
	const params: (string | number)[] = [];

	if (filters?.query) {
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

	if (filters?.category) {
		conditions.push(`w.category = ?`);
		params.push(filters.category);
	}

	if (filters?.workType) {
		conditions.push(`w.work_type = ?`);
		params.push(filters.workType);
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

export interface CategoryCounts {
	teater: number;
	opera: number;
	konsert: number;
	dramaserie: number;
}

export function getCategoryCounts(): CategoryCounts {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT w.category, COUNT(DISTINCT perf.id) as count
		FROM performances perf
		LEFT JOIN works w ON perf.work_id = w.id
		GROUP BY w.category
	`);

	const result: CategoryCounts = { teater: 0, opera: 0, konsert: 0, dramaserie: 0 };
	while (stmt.step()) {
		const row = stmt.getAsObject() as { category: string | null; count: number };
		const cat = row.category as keyof CategoryCounts;
		if (cat && cat in result) {
			result[cat] = row.count;
		}
	}
	stmt.free();

	return result;
}

export interface WorkTypeCounts {
	teaterstykke: number;
	nrk_teaterstykke: number;
	dramaserie: number;
	opera: number;
	konsert: number;
}

export function getWorkTypeCounts(): WorkTypeCounts {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT w.work_type, COUNT(DISTINCT perf.id) as count
		FROM performances perf
		LEFT JOIN works w ON perf.work_id = w.id
		GROUP BY w.work_type
	`);

	const result: WorkTypeCounts = { teaterstykke: 0, nrk_teaterstykke: 0, dramaserie: 0, opera: 0, konsert: 0 };
	while (stmt.step()) {
		const row = stmt.getAsObject() as { work_type: string | null; count: number };
		const wt = row.work_type as keyof WorkTypeCounts;
		if (wt && wt in result) {
			result[wt] = row.count;
		}
	}
	stmt.free();

	return result;
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
		ORDER BY episode_number ASC NULLS LAST, prf_id ASC
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
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'conductor' LIMIT 1
			)) as conductor_name,
			(SELECT COALESCE(i.short_name, i.name) FROM institutions i
				JOIN performance_institutions pi ON pi.institution_id = i.id
				WHERE pi.performance_id = perf.id AND i.type = 'orchestra' LIMIT 1
			) as orchestra_name,
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

export function getWorkPerformancesByMedium(workId: number, medium: 'tv' | 'radio' | 'stream'): PerformanceWithDetails[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			perf.*,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'conductor' LIMIT 1
			)) as conductor_name,
			(SELECT i.name FROM institutions i
				JOIN performance_institutions pi ON pi.institution_id = i.id
				WHERE pi.performance_id = perf.id AND pi.role = 'orchestra' LIMIT 1
			) as orchestra_name,
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
			COUNT(DISTINCT w.id) as play_count,
			COUNT(DISTINCT perf.id) as performance_count
		FROM persons p
		JOIN works w ON p.id = w.playwright_id
		JOIN performances perf ON perf.work_id = w.id
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
		JOIN works w ON p.id = w.playwright_id
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

	let orderBy = 'w.title ASC';
	if (sortBy === 'year') orderBy = 'w.year_written DESC NULLS LAST, w.title ASC';
	if (sortBy === 'playwright') orderBy = 'playwright.name ASC NULLS LAST, w.title ASC';

	const stmt = db.prepare(`
		SELECT
			w.id,
			w.title,
			w.original_title,
			w.year_written,
			w.playwright_id,
			playwright.name as playwright_name,
			COUNT(DISTINCT perf.id) as performance_count
		FROM works w
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		LEFT JOIN performances perf ON perf.work_id = w.id
		GROUP BY w.id
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
		SELECT COUNT(DISTINCT w.id) as count
		FROM works w
		JOIN performances perf ON perf.work_id = w.id
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

// Alias
export const getWorkCount = getPlayCount;

export function getAuthorCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(DISTINCT p.id) as count
		FROM persons p
		JOIN works w ON p.id = w.playwright_id
		JOIN performances perf ON perf.work_id = w.id
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

// ===== External Resources (Concerts, etc.) =====

export function searchExternalResources(
	filters: ExternalResourceFilters,
	limit = 50,
	offset = 0
): ExternalResource[] {
	const db = getDatabase();

	let sql = `SELECT * FROM external_resources WHERE is_working = 1`;
	const params: (string | number)[] = [];

	if (filters.type) {
		sql += ` AND type = ?`;
		params.push(filters.type);
	}

	if (filters.query) {
		sql += ` AND (title LIKE ? OR description LIKE ?)`;
		const term = `%${filters.query}%`;
		params.push(term, term);
	}

	if (filters.composer) {
		sql += ` AND (title LIKE ? OR description LIKE ?)`;
		const term = `%${filters.composer}%`;
		params.push(term, term);
	}

	sql += ` ORDER BY title ASC LIMIT ? OFFSET ?`;
	params.push(limit, offset);

	const stmt = db.prepare(sql);
	stmt.bind(params);

	const results: ExternalResource[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as ExternalResource);
	}
	stmt.free();

	return results;
}

export function getExternalResourceCount(filters?: ExternalResourceFilters): number {
	const db = getDatabase();

	let sql = `SELECT COUNT(*) as count FROM external_resources WHERE is_working = 1`;
	const params: (string | number)[] = [];

	if (filters?.type) {
		sql += ` AND type = ?`;
		params.push(filters.type);
	}

	if (filters?.query) {
		sql += ` AND (title LIKE ? OR description LIKE ?)`;
		const term = `%${filters.query}%`;
		params.push(term, term);
	}

	if (filters?.composer) {
		sql += ` AND (title LIKE ? OR description LIKE ?)`;
		const term = `%${filters.composer}%`;
		params.push(term, term);
	}

	const stmt = db.prepare(sql);
	stmt.bind(params);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();

	return result.count;
}

export function getExternalResourceTypes(): { type: string; count: number }[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT type, COUNT(*) as count
		FROM external_resources
		WHERE is_working = 1
		GROUP BY type
		ORDER BY count DESC
	`);

	const results: { type: string; count: number }[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as { type: string; count: number });
	}
	stmt.free();

	return results;
}

export function getBergenPhilConcertCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(*) as count FROM external_resources
		WHERE type = 'bergenphilive' AND is_working = 1
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

// ===== Landing Page Discovery =====

export interface RandomPerformance extends PerformanceWithDetails {
	work_synopsis?: string | null;
}

export function getRandomClassicalPlays(limit = 6): RandomPerformance[] {
	const db = getDatabase();

	// Get random performances of classical plays (teaterstykke only, not nrk_teaterstykke)
	const stmt = db.prepare(`
		SELECT
			perf.*,
			w.title as work_title,
			w.playwright_id,
			w.work_type,
			w.category,
			w.synopsis as work_synopsis,
			playwright.name as playwright_name,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		JOIN works w ON perf.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		WHERE w.work_type = 'teaterstykke'
		ORDER BY RANDOM()
		LIMIT ?
	`);
	stmt.bind([limit]);

	const results: RandomPerformance[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as RandomPerformance);
	}
	stmt.free();

	return results;
}

export function getPlaysByPlaywright(playwrightId: number, limit = 10): PerformanceWithDetails[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			perf.*,
			w.title as work_title,
			w.playwright_id,
			w.work_type,
			w.category,
			playwright.name as playwright_name,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		JOIN works w ON perf.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		WHERE w.playwright_id = ?
		ORDER BY perf.year DESC
		LIMIT ?
	`);
	stmt.bind([playwrightId, limit]);

	const results: PerformanceWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PerformanceWithDetails);
	}
	stmt.free();

	return results;
}

export interface WorkWithCounts extends Work {
	performance_count: number;
	playwright_name?: string | null;
	composer_name?: string | null;
	image_url?: string | null;
}

export function getWorksByPlaywright(playwrightId: number, excludeWorkId: number, limit = 10): WorkWithCounts[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			w.*,
			playwright.name as playwright_name,
			composer.name as composer_name,
			COUNT(DISTINCT perf.id) as performance_count,
			(SELECT e.image_url FROM episodes e
			 JOIN performances p ON e.performance_id = p.id
			 WHERE p.work_id = w.id AND e.image_url IS NOT NULL
			 LIMIT 1) as image_url
		FROM works w
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		LEFT JOIN persons composer ON w.composer_id = composer.id
		LEFT JOIN performances perf ON perf.work_id = w.id
		WHERE w.playwright_id = ? AND w.id != ?
		GROUP BY w.id
		HAVING performance_count > 0
		ORDER BY performance_count DESC, w.title ASC
		LIMIT ?
	`);
	stmt.bind([playwrightId, excludeWorkId, limit]);

	const results: WorkWithCounts[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as WorkWithCounts);
	}
	stmt.free();

	return results;
}

export function getPerformancesByDecade(startYear: number, endYear: number, limit = 10): PerformanceWithDetails[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			perf.*,
			w.title as work_title,
			w.playwright_id,
			w.work_type,
			w.category,
			playwright.name as playwright_name,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		JOIN works w ON perf.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		WHERE perf.year >= ? AND perf.year <= ?
		ORDER BY RANDOM()
		LIMIT ?
	`);
	stmt.bind([startYear, endYear, limit]);

	const results: PerformanceWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as PerformanceWithDetails);
	}
	stmt.free();

	return results;
}

export function getRecentConcerts(limit = 10): ExternalResource[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT * FROM external_resources
		WHERE type = 'bergenphilive' AND is_working = 1
		ORDER BY RANDOM()
		LIMIT ?
	`);
	stmt.bind([limit]);

	const results: ExternalResource[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as ExternalResource);
	}
	stmt.free();

	return results;
}

export function getClassicalPlayCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(DISTINCT w.id) as count
		FROM works w
		JOIN performances perf ON perf.work_id = w.id
		WHERE w.work_type = 'teaterstykke'
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

export function getTheaterPerformanceCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(*) as count
		FROM performances perf
		JOIN works w ON perf.work_id = w.id
		WHERE w.category = 'teater'
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

export function getConcertPerformanceCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(*) as count
		FROM performances perf
		JOIN works w ON perf.work_id = w.id
		WHERE w.category = 'konsert'
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

export function getOperaPerformanceCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(*) as count
		FROM performances perf
		JOIN works w ON perf.work_id = w.id
		WHERE w.category = 'opera'
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

export function getCreatorCount(): number {
	const db = getDatabase();
	const stmt = db.prepare(`
		SELECT COUNT(DISTINCT p.id) as count
		FROM persons p
		WHERE EXISTS (SELECT 1 FROM works w WHERE w.playwright_id = p.id)
		   OR EXISTS (SELECT 1 FROM works w WHERE w.composer_id = p.id)
	`);
	stmt.step();
	const result = stmt.getAsObject() as { count: number };
	stmt.free();
	return result.count;
}

export function getDb(): Database | null {
	return db;
}

export function getExternalResourceComposers(): string[] {
	const db = getDatabase();

	// Extract composer from titles like "Grieg: Pianokonsert"
	const stmt = db.prepare(`
		SELECT DISTINCT
			CASE
				WHEN title LIKE '%:%' THEN TRIM(SUBSTR(title, 1, INSTR(title, ':') - 1))
				ELSE NULL
			END as composer
		FROM external_resources
		WHERE type = 'bergenphilive' AND is_working = 1
		AND composer IS NOT NULL
		ORDER BY composer
	`);

	const results: string[] = [];
	while (stmt.step()) {
		const row = stmt.getAsObject() as { composer: string | null };
		if (row.composer) {
			results.push(row.composer);
		}
	}
	stmt.free();

	return results;
}

// ===== Global Search =====

export interface SearchResultPerson extends Person {
	work_count: number;
	performance_count: number;
	roles: string[];
}

export interface SearchResultWork extends Work {
	playwright_name: string | null;
	composer_name: string | null;
	performance_count: number;
	image_url: string | null;
}

export interface SearchResultPerformance extends PerformanceWithDetails {
	// Already has work_title, playwright_name, director_name, media_count, etc.
}

export interface SearchAllResults {
	persons: SearchResultPerson[];
	works: SearchResultWork[];
	performances: SearchResultPerformance[];
}

export function searchAll(query: string, limit = 10): SearchAllResults {
	const db = getDatabase();
	const term = `%${query}%`;
	const normalizedTerm = `%${query.toLowerCase()}%`;

	// Search persons (those with works as playwright/composer/librettist OR with performance credits)
	const personsStmt = db.prepare(`
		SELECT
			p.*,
			(SELECT COUNT(DISTINCT w.id) FROM works w WHERE w.playwright_id = p.id OR w.composer_id = p.id OR w.librettist_id = p.id) +
			(SELECT COUNT(DISTINCT wc.work_id) FROM work_composers wc WHERE wc.person_id = p.id) as work_count,
			(SELECT COUNT(DISTINCT pp.performance_id) FROM performance_persons pp WHERE pp.person_id = p.id) as performance_count,
			(SELECT GROUP_CONCAT(DISTINCT pp.role) FROM performance_persons pp WHERE pp.person_id = p.id) as roles_str
		FROM persons p
		WHERE (p.name LIKE ? OR p.normalized_name LIKE ?)
		AND (
			(SELECT COUNT(DISTINCT w.id) FROM works w WHERE w.playwright_id = p.id OR w.composer_id = p.id OR w.librettist_id = p.id) > 0
			OR (SELECT COUNT(DISTINCT wc.work_id) FROM work_composers wc WHERE wc.person_id = p.id) > 0
			OR (SELECT COUNT(DISTINCT pp.performance_id) FROM performance_persons pp WHERE pp.person_id = p.id) > 0
		)
		ORDER BY
			CASE WHEN p.name LIKE ? THEN 0 ELSE 1 END,
			work_count DESC,
			performance_count DESC
		LIMIT ?
	`);
	personsStmt.bind([term, normalizedTerm, query + '%', limit]);

	const persons: SearchResultPerson[] = [];
	while (personsStmt.step()) {
		const row = personsStmt.getAsObject() as any;
		persons.push({
			...row,
			roles: row.roles_str ? row.roles_str.split(',') : []
		});
	}
	personsStmt.free();

	// Search works
	const worksStmt = db.prepare(`
		SELECT
			w.*,
			playwright.name as playwright_name,
			composer.name as composer_name,
			(SELECT COUNT(*) FROM performances perf WHERE perf.work_id = w.id) as performance_count,
			(SELECT e.image_url FROM episodes e JOIN performances perf ON e.performance_id = perf.id WHERE perf.work_id = w.id LIMIT 1) as image_url
		FROM works w
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		LEFT JOIN persons composer ON w.composer_id = composer.id
		WHERE w.title LIKE ? OR w.original_title LIKE ?
		ORDER BY
			CASE WHEN w.title LIKE ? THEN 0 ELSE 1 END,
			performance_count DESC,
			w.title
		LIMIT ?
	`);
	worksStmt.bind([term, term, query + '%', limit]);

	const works: SearchResultWork[] = [];
	while (worksStmt.step()) {
		works.push(worksStmt.getAsObject() as unknown as SearchResultWork);
	}
	worksStmt.free();

	// Search performances
	const performancesStmt = db.prepare(`
		SELECT
			perf.*,
			w.title as work_title,
			w.playwright_id,
			w.work_type,
			w.category,
			playwright.name as playwright_name,
			(SELECT name FROM persons WHERE id = (
				SELECT person_id FROM performance_persons pp
				WHERE pp.performance_id = perf.id AND pp.role = 'director' LIMIT 1
			)) as director_name,
			(SELECT COUNT(*) FROM episodes e WHERE e.performance_id = perf.id) as media_count,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		LEFT JOIN works w ON perf.work_id = w.id
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		WHERE perf.title LIKE ? OR perf.description LIKE ? OR w.title LIKE ?
		ORDER BY
			CASE WHEN perf.title LIKE ? OR w.title LIKE ? THEN 0 ELSE 1 END,
			perf.year DESC
		LIMIT ?
	`);
	performancesStmt.bind([term, term, term, query + '%', query + '%', limit]);

	const performances: SearchResultPerformance[] = [];
	while (performancesStmt.step()) {
		performances.push(performancesStmt.getAsObject() as unknown as SearchResultPerformance);
	}
	performancesStmt.free();

	return { persons, works, performances };
}

// Autocomplete search - returns quick suggestions for search box dropdown
export interface AutocompleteSuggestion {
	type: 'person' | 'work' | 'performance';
	id: number | string;
	title: string;
	subtitle: string | null;
	url: string;
	image_url: string | null;
}

export function getAutocompleteSuggestions(query: string, limit = 8): AutocompleteSuggestion[] {
	const db = getDatabase();
	const term = `%${query}%`;
	const startTerm = query + '%';
	const suggestions: AutocompleteSuggestion[] = [];

	// Get person suggestions (limit to 3, people with works OR performance credits)
	const personsStmt = db.prepare(`
		SELECT
			p.id,
			p.name,
			p.birth_year,
			p.death_year,
			(SELECT COUNT(DISTINCT w.id) FROM works w WHERE w.playwright_id = p.id OR w.composer_id = p.id) +
			(SELECT COUNT(DISTINCT wc.work_id) FROM work_composers wc WHERE wc.person_id = p.id) as work_count,
			(SELECT COUNT(DISTINCT pp.performance_id) FROM performance_persons pp WHERE pp.person_id = p.id) as performance_count,
			(SELECT GROUP_CONCAT(DISTINCT pp.role) FROM performance_persons pp WHERE pp.person_id = p.id) as roles_str
		FROM persons p
		WHERE (p.name LIKE ? OR p.normalized_name LIKE ?)
		AND (
			(SELECT COUNT(DISTINCT w.id) FROM works w WHERE w.playwright_id = p.id OR w.composer_id = p.id) > 0
			OR (SELECT COUNT(DISTINCT wc.work_id) FROM work_composers wc WHERE wc.person_id = p.id) > 0
			OR (SELECT COUNT(DISTINCT pp.performance_id) FROM performance_persons pp WHERE pp.person_id = p.id) > 0
		)
		ORDER BY
			CASE WHEN p.name LIKE ? THEN 0 ELSE 1 END,
			work_count DESC,
			performance_count DESC
		LIMIT 3
	`);
	personsStmt.bind([term, term, startTerm]);

	while (personsStmt.step()) {
		const row = personsStmt.getAsObject() as any;
		const years = row.birth_year
			? `${row.birth_year}–${row.death_year || ''}`
			: null;
		// Build subtitle based on what they have
		let subtitle: string;
		if (row.work_count > 0) {
			subtitle = years ? `${years} · ${row.work_count} verk` : `${row.work_count} verk`;
		} else {
			// Show role for people without works (conductors, directors, etc.)
			const roles = row.roles_str ? row.roles_str.split(',') : [];
			const roleLabel = roles.includes('conductor') ? 'Dirigent' :
				roles.includes('director') ? 'Regissør' :
				roles.includes('actor') ? 'Skuespiller' : 'Medvirkende';
			subtitle = years ? `${years} · ${roleLabel}` : `${roleLabel} · ${row.performance_count} opptak`;
		}
		suggestions.push({
			type: 'person',
			id: row.id,
			title: row.name,
			subtitle,
			url: `/person/${row.id}`,
			image_url: null
		});
	}
	personsStmt.free();

	// Get work suggestions (limit to 3)
	const worksStmt = db.prepare(`
		SELECT
			w.id,
			w.title,
			playwright.name as playwright_name,
			composer.name as composer_name,
			(SELECT COUNT(*) FROM performances perf WHERE perf.work_id = w.id) as performance_count,
			(SELECT e.image_url FROM episodes e JOIN performances perf ON e.performance_id = perf.id WHERE perf.work_id = w.id LIMIT 1) as image_url
		FROM works w
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		LEFT JOIN persons composer ON w.composer_id = composer.id
		WHERE w.title LIKE ? OR w.original_title LIKE ?
		ORDER BY
			CASE WHEN w.title LIKE ? THEN 0 ELSE 1 END,
			performance_count DESC
		LIMIT 3
	`);
	worksStmt.bind([term, term, startTerm]);

	while (worksStmt.step()) {
		const row = worksStmt.getAsObject() as any;
		const creator = row.playwright_name || row.composer_name;
		suggestions.push({
			type: 'work',
			id: row.id,
			title: row.title,
			subtitle: creator ? `${creator} · ${row.performance_count} opptak` : `${row.performance_count} opptak`,
			url: `/verk/${row.id}`,
			image_url: row.image_url
		});
	}
	worksStmt.free();

	// Get performance suggestions (limit to 2)
	const performancesStmt = db.prepare(`
		SELECT
			perf.id,
			COALESCE(perf.title, w.title) as title,
			perf.year,
			perf.medium,
			w.title as work_title,
			(SELECT e.image_url FROM episodes e WHERE e.performance_id = perf.id LIMIT 1) as image_url
		FROM performances perf
		LEFT JOIN works w ON perf.work_id = w.id
		WHERE perf.title LIKE ? OR w.title LIKE ?
		ORDER BY
			CASE WHEN perf.title LIKE ? OR w.title LIKE ? THEN 0 ELSE 1 END,
			perf.year DESC
		LIMIT 2
	`);
	performancesStmt.bind([term, term, startTerm, startTerm]);

	while (performancesStmt.step()) {
		const row = performancesStmt.getAsObject() as any;
		const mediumLabel = row.medium === 'tv' ? 'TV' : 'Radio';
		suggestions.push({
			type: 'performance',
			id: row.id,
			title: row.title,
			subtitle: row.year ? `${row.year} · ${mediumLabel}` : mediumLabel,
			url: `/opptak/${row.id}`,
			image_url: row.image_url
		});
	}
	performancesStmt.free();

	return suggestions.slice(0, limit);
}

// ===== Work Relationships =====

export interface WorkWithDetails extends Work {
	playwright_name: string | null;
	composer_name: string | null;
	performance_count: number;
	image_url: string | null;
}

// Get the work this work is based on (e.g., Grieg's Peer Gynt Suite → Ibsen's Peer Gynt)
export function getSourceWork(workId: number): WorkWithDetails | null {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			w.*,
			playwright.name as playwright_name,
			composer.name as composer_name,
			(SELECT COUNT(*) FROM performances perf WHERE perf.work_id = w.id) as performance_count,
			(SELECT e.image_url FROM episodes e JOIN performances perf ON e.performance_id = perf.id WHERE perf.work_id = w.id LIMIT 1) as image_url
		FROM works w
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		LEFT JOIN persons composer ON w.composer_id = composer.id
		WHERE w.id = (SELECT based_on_work_id FROM works WHERE id = ?)
	`);
	stmt.bind([workId]);

	let result: WorkWithDetails | null = null;
	if (stmt.step()) {
		result = stmt.getAsObject() as unknown as WorkWithDetails;
	}
	stmt.free();

	return result;
}

// Get works that are adaptations of this work (e.g., Peer Gynt → Peer Gynt Suite, Peer Gynt opera)
export function getAdaptations(workId: number): WorkWithDetails[] {
	const db = getDatabase();

	const stmt = db.prepare(`
		SELECT
			w.*,
			playwright.name as playwright_name,
			composer.name as composer_name,
			(SELECT COUNT(*) FROM performances perf WHERE perf.work_id = w.id) as performance_count,
			(SELECT e.image_url FROM episodes e JOIN performances perf ON e.performance_id = perf.id WHERE perf.work_id = w.id LIMIT 1) as image_url
		FROM works w
		LEFT JOIN persons playwright ON w.playwright_id = playwright.id
		LEFT JOIN persons composer ON w.composer_id = composer.id
		WHERE w.based_on_work_id = ?
		ORDER BY w.year_written, w.title
	`);
	stmt.bind([workId]);

	const results: WorkWithDetails[] = [];
	while (stmt.step()) {
		results.push(stmt.getAsObject() as unknown as WorkWithDetails);
	}
	stmt.free();

	return results;
}
