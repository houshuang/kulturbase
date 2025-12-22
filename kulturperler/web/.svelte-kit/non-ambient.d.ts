
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
		RouteId(): "/" | "/dramaserier" | "/episode" | "/episode/[id]" | "/konserter" | "/om" | "/opera" | "/opptak" | "/opptak/[id]" | "/performance" | "/performance/[id]" | "/personer" | "/persons" | "/person" | "/person/[id]" | "/sok" | "/teater" | "/verk" | "/verk/play" | "/verk/play/[id]" | "/verk/[id]" | "/work" | "/work/[id]";
		RouteParams(): {
			"/episode/[id]": { id: string };
			"/opptak/[id]": { id: string };
			"/performance/[id]": { id: string };
			"/person/[id]": { id: string };
			"/verk/play/[id]": { id: string };
			"/verk/[id]": { id: string };
			"/work/[id]": { id: string }
		};
		LayoutParams(): {
			"/": { id?: string };
			"/dramaserier": Record<string, never>;
			"/episode": { id?: string };
			"/episode/[id]": { id: string };
			"/konserter": Record<string, never>;
			"/om": Record<string, never>;
			"/opera": Record<string, never>;
			"/opptak": { id?: string };
			"/opptak/[id]": { id: string };
			"/performance": { id?: string };
			"/performance/[id]": { id: string };
			"/personer": Record<string, never>;
			"/persons": Record<string, never>;
			"/person": { id?: string };
			"/person/[id]": { id: string };
			"/sok": Record<string, never>;
			"/teater": Record<string, never>;
			"/verk": { id?: string };
			"/verk/play": { id?: string };
			"/verk/play/[id]": { id: string };
			"/verk/[id]": { id: string };
			"/work": { id?: string };
			"/work/[id]": { id: string }
		};
		Pathname(): "/" | "/dramaserier" | "/dramaserier/" | "/episode" | "/episode/" | `/episode/${string}` & {} | `/episode/${string}/` & {} | "/konserter" | "/konserter/" | "/om" | "/om/" | "/opera" | "/opera/" | "/opptak" | "/opptak/" | `/opptak/${string}` & {} | `/opptak/${string}/` & {} | "/performance" | "/performance/" | `/performance/${string}` & {} | `/performance/${string}/` & {} | "/personer" | "/personer/" | "/persons" | "/persons/" | "/person" | "/person/" | `/person/${string}` & {} | `/person/${string}/` & {} | "/sok" | "/sok/" | "/teater" | "/teater/" | "/verk" | "/verk/" | "/verk/play" | "/verk/play/" | `/verk/play/${string}` & {} | `/verk/play/${string}/` & {} | `/verk/${string}` & {} | `/verk/${string}/` & {} | "/work" | "/work/" | `/work/${string}` & {} | `/work/${string}/` & {};
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/favicon.png" | "/favicon.svg" | "/images/peasant-dance.jpg" | "/kulturperler.db" | "/kulturperler.db.backup_20251219_122607" | "/kulturperler.db.backup_20251219_153151" | "/kulturperler.db.backup_20251219_155403" | "/kulturperler.db.backup_20251219_155433" | "/nrk_about_cache.json" | "/nrk_candidates.json" | "/sceneweb_cache.json" | string & {};
	}
}