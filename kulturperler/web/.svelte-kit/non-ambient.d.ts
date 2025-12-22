
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	export interface AppTypes {
		RouteId(): "/" | "/dramaserier" | "/episode" | "/episode/[id]" | "/konserter" | "/opera" | "/performance" | "/performance/[id]" | "/persons" | "/person" | "/person/[id]" | "/play" | "/play/[id]" | "/skapere" | "/teater" | "/work" | "/work/[id]";
		RouteParams(): {
			"/episode/[id]": { id: string };
			"/performance/[id]": { id: string };
			"/person/[id]": { id: string };
			"/play/[id]": { id: string };
			"/work/[id]": { id: string }
		};
		LayoutParams(): {
			"/": { id?: string };
			"/dramaserier": Record<string, never>;
			"/episode": { id?: string };
			"/episode/[id]": { id: string };
			"/konserter": Record<string, never>;
			"/opera": Record<string, never>;
			"/performance": { id?: string };
			"/performance/[id]": { id: string };
			"/persons": Record<string, never>;
			"/person": { id?: string };
			"/person/[id]": { id: string };
			"/play": { id?: string };
			"/play/[id]": { id: string };
			"/skapere": Record<string, never>;
			"/teater": Record<string, never>;
			"/work": { id?: string };
			"/work/[id]": { id: string }
		};
		Pathname(): "/" | "/dramaserier" | "/dramaserier/" | "/episode" | "/episode/" | `/episode/${string}` & {} | `/episode/${string}/` & {} | "/konserter" | "/konserter/" | "/opera" | "/opera/" | "/performance" | "/performance/" | `/performance/${string}` & {} | `/performance/${string}/` & {} | "/persons" | "/persons/" | "/person" | "/person/" | `/person/${string}` & {} | `/person/${string}/` & {} | "/play" | "/play/" | `/play/${string}` & {} | `/play/${string}/` & {} | "/skapere" | "/skapere/" | "/teater" | "/teater/" | "/work" | "/work/" | `/work/${string}` & {} | `/work/${string}/` & {};
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/favicon.png" | "/kulturperler.db" | "/kulturperler.db.backup_20251219_122607" | "/kulturperler.db.backup_20251219_153151" | "/kulturperler.db.backup_20251219_155403" | "/kulturperler.db.backup_20251219_155433" | "/nrk_about_cache.json" | "/nrk_candidates.json" | "/sceneweb_cache.json" | string & {};
	}
}