export const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set(["favicon.png","kulturperler.db","kulturperler.db.backup_20251219_122607","kulturperler.db.backup_20251219_153151","kulturperler.db.backup_20251219_155403","kulturperler.db.backup_20251219_155433","nrk_about_cache.json","nrk_candidates.json","sceneweb_cache.json"]),
	mimeTypes: {".png":"image/png",".json":"application/json"},
	_: {
		client: {start:"_app/immutable/entry/start.CnjvATn_.js",app:"_app/immutable/entry/app.D1Wi00pv.js",imports:["_app/immutable/entry/start.CnjvATn_.js","_app/immutable/chunks/B52t6YnV.js","_app/immutable/chunks/D2mf_MPo.js","_app/immutable/chunks/B_RZd05l.js","_app/immutable/entry/app.D1Wi00pv.js","_app/immutable/chunks/D2mf_MPo.js","_app/immutable/chunks/DLNOMP84.js","_app/immutable/chunks/BDyHfgtg.js","_app/immutable/chunks/DlPtdyWE.js","_app/immutable/chunks/B_RZd05l.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/2.js')),
			__memo(() => import('./nodes/3.js')),
			__memo(() => import('./nodes/4.js')),
			__memo(() => import('./nodes/5.js')),
			__memo(() => import('./nodes/6.js')),
			__memo(() => import('./nodes/7.js'))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			},
			{
				id: "/episode/[id]",
				pattern: /^\/episode\/([^/]+?)\/?$/,
				params: [{"name":"id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 3 },
				endpoint: null
			},
			{
				id: "/performance/[id]",
				pattern: /^\/performance\/([^/]+?)\/?$/,
				params: [{"name":"id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 4 },
				endpoint: null
			},
			{
				id: "/persons",
				pattern: /^\/persons\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 6 },
				endpoint: null
			},
			{
				id: "/person/[id]",
				pattern: /^\/person\/([^/]+?)\/?$/,
				params: [{"name":"id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 5 },
				endpoint: null
			},
			{
				id: "/play/[id]",
				pattern: /^\/play\/([^/]+?)\/?$/,
				params: [{"name":"id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 7 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();
