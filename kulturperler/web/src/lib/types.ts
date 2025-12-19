export interface Episode {
	prf_id: string;
	title: string;
	description: string | null;
	year: number | null;
	duration_seconds: number | null;
	image_url: string | null;
	nrk_url: string | null;
	play_id: number | null;
	source: string;
	part_number: number | null;
	total_parts: number | null;
	is_introduction: number | null;
	parent_episode_id: string | null;
	performance_id: number | null;
	media_type: 'episode' | 'part' | 'intro' | null;
}

// Alias for clarity - Play = Work in our ontology
export type Work = Play & {
	work_type?: string;
	synopsis?: string;
};

export interface Performance {
	id: number;
	work_id: number | null;
	source: string;
	year: number | null;
	title: string | null;
	description: string | null;
	venue: string | null;
	total_duration: number | null;
	image_url: string | null;
}

export interface PerformanceWithDetails extends Performance {
	work_title?: string | null;
	playwright_name?: string | null;
	playwright_id?: number | null;
	director_name?: string | null;
	media_count?: number;
}

export interface PerformancePerson {
	id: number;
	performance_id: number;
	person_id: number;
	role: string | null;
	character_name: string | null;
}

export interface Person {
	id: number;
	name: string;
	normalized_name: string | null;
	birth_year: number | null;
	death_year: number | null;
	nationality: string | null;
	wikidata_id: string | null;
	sceneweb_id: number | null;
	sceneweb_url: string | null;
	wikipedia_url: string | null;
	bio: string | null;
	image_url: string | null;
}

export interface Play {
	id: number;
	title: string;
	original_title: string | null;
	playwright_id: number | null;
	year_written: number | null;
	wikidata_id: string | null;
	sceneweb_id: number | null;
	sceneweb_url: string | null;
	wikipedia_url: string | null;
	synopsis: string | null;
}

export interface Tag {
	id: number;
	name: string;
	display_name: string;
	color: string | null;
}

export interface EpisodePerson {
	episode_id: string;
	person_id: number;
	role: string | null;
	character_name: string | null;
}

export interface SearchFilters {
	query?: string;
	yearFrom?: number;
	yearTo?: number;
	playwrightId?: number;
	directorId?: number;
	actorId?: number;
	tagIds?: number[];
}

export interface EpisodeWithDetails extends Episode {
	playwright_name?: string | null;
	director_name?: string | null;
	play_title?: string | null;
}

export type PersonRole = 'director' | 'actor' | 'playwright' | 'composer' | 'set_designer' | 'costume_designer' | 'producer' | 'other';

export interface PlayExternalLink {
	id: number;
	play_id: number | null;
	url: string;
	title: string;
	type: string;
	description: string | null;
	access_note: string | null;
}

export interface NrkAboutProgram {
	id: string;
	person_id: number;
	title: string;
	description: string | null;
	duration_seconds: number | null;
	image_url: string | null;
	nrk_url: string;
	program_type: string;
	year: number | null;
	interest_score: number;
	episode_count: number | null;
}
