export type Medium = 'tv' | 'radio' | 'stream';

export type WorkType = 'teaterstykke' | 'nrk_teaterstykke' | 'dramaserie' | 'opera' | 'konsert';
export type WorkCategory = 'teater' | 'opera' | 'konsert' | 'dramaserie';

export interface Episode {
	prf_id: string;
	title: string;
	description: string | null;
	year: number | null;
	duration_seconds: number | null;
	image_url: string | null;
	nrk_url: string | null;
	youtube_url: string | null;
	work_id: number | null;
	play_id?: number | null; // Deprecated alias for work_id
	source: string;
	part_number: number | null;
	total_parts: number | null;
	is_introduction: number | null;
	parent_episode_id: string | null;
	performance_id: number | null;
	media_type: 'episode' | 'part' | 'intro' | null;
	medium: Medium;
}

export interface Work {
	id: number;
	title: string;
	original_title: string | null;
	work_type: WorkType | null;
	category: WorkCategory | null;
	playwright_id: number | null;
	composer_id: number | null;
	librettist_id: number | null;
	creator_id: number | null;
	year_written: number | null;
	synopsis: string | null;
	based_on_work_id: number | null;
	wikidata_id: string | null;
	sceneweb_id: number | null;
	sceneweb_url: string | null;
	wikipedia_url: string | null;
}

// Alias for backwards compatibility
export type Play = Work;

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
	medium: Medium;
}

export interface PerformanceWithDetails extends Performance {
	work_title?: string | null;
	playwright_name?: string | null;
	playwright_id?: number | null;
	director_name?: string | null;
	conductor_name?: string | null;
	orchestra_name?: string | null;
	media_count?: number;
	work_type?: WorkType | null;
	category?: WorkCategory | null;
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
	bokselskap_url: string | null;
}

export interface Institution {
	id: number;
	name: string;
	short_name: string | null;
	type: 'orchestra' | 'theater' | 'opera_house' | 'ensemble';
	location: string | null;
	founded_year: number | null;
	bio: string | null;
	wikipedia_url: string | null;
	image_url: string | null;
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
	mediums?: Medium[];
	category?: WorkCategory;
	workType?: WorkType;
}

export interface EpisodeWithDetails extends Episode {
	playwright_name?: string | null;
	director_name?: string | null;
	play_title?: string | null;
	work_title?: string | null;
}

export type PersonRole =
	| 'director'
	| 'actor'
	| 'playwright'
	| 'composer'
	| 'arranger'
	| 'orchestrator'
	| 'lyricist'
	| 'adapter'
	| 'conductor'
	| 'soloist'
	| 'librettist'
	| 'set_designer'
	| 'costume_designer'
	| 'producer'
	| 'other';

// Composer roles for works
export type ComposerRole = 'composer' | 'arranger' | 'orchestrator' | 'lyricist' | 'adapter';

// Work composer junction record
export interface WorkComposer {
	work_id: number;
	person_id: number;
	role: ComposerRole;
	sort_order: number;
	// Joined fields
	person_name?: string;
	person_birth_year?: number | null;
	person_death_year?: number | null;
}

export interface WorkExternalLink {
	id: number;
	work_id: number | null;
	url: string;
	title: string;
	type: string;
	description: string | null;
	access_note: string | null;
}

// Alias for backwards compatibility
export type PlayExternalLink = WorkExternalLink;

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

export interface ExternalResource {
	id: number;
	url: string;
	title: string;
	type: string;
	description: string | null;
	added_date: string | null;
	is_working: number;
}

export interface ExternalResourceFilters {
	query?: string;
	type?: string;
	composer?: string;
}
