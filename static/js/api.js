/**
 * AutoShift - API操作・データ管理JavaScript
 * 2026年2月9日
 */

// AutoShift名前空間にAPI関連機能を追加
window.AutoShift = window.AutoShift || {};

// ====================
// API エンドポイント定義
// ====================

AutoShift.API.endpoints = {
    // シフト関連
    shift: {
        generate: '/api/shift/generate',
        result: (month) => `/api/shift/result/${month}`,
        display: (month) => `/api/shift/display/${month}`,
        validate: (month) => `/api/shift/display/validate/${month}`,
        export: (month, format) => `/api/shift/display/export/${month}/${format}`
    },
    
    // ルール関連
    rules: {
        facility: '/api/rules/facility',
        facilityById: (id) => `/api/rules/facility/${id}`,
        validate: '/api/rules/validate'
    },
    
    // 希望休関連
    holidays: {
        staff: '/api/holidays/staff',
        request: (month) => `/api/holidays/request/${month}`,
        requestById: (month, staffId, date) => `/api/holidays/request/${month}/${staffId}/${date}`,
        bulk: (month) => `/api/holidays/request/${month}/bulk`,
        calendar: (month) => `/api/holidays/calendar/${month}`
    },
    
    // システム関連
    system: {
        health: '/api/health'
    }
};

// ====================
// シフト管理API
// ====================

AutoShift.ShiftAPI = {
    /**
     * シフト生成
     */
    generate: async (month) => {
        try {
            const result = await AutoShift.API.post(AutoShift.API.endpoints.shift.generate, {
                month: month
            });
            
            if (result.status === 'success') {
                AutoShift.Alert.success(`${month}のシフトを生成しました`);
                return result.data;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            AutoShift.Alert.error(`シフト生成に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * シフト結果取得
     */
    getResult: async (month) => {
        try {
            const result = await AutoShift.API.get(AutoShift.API.endpoints.shift.result(month));
            return result.data;
        } catch (error) {
            AutoShift.Alert.error(`シフト結果取得に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * シフト表示データ取得
     */
    getDisplayData: async (month) => {
        try {
            const result = await AutoShift.API.get(AutoShift.API.endpoints.shift.display(month));
            return result.data;
        } catch (error) {
            AutoShift.Alert.error(`シフト表示データ取得に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * シフト検証
     */
    validate: async (month) => {
        try {
            const result = await AutoShift.API.get(AutoShift.API.endpoints.shift.validate(month));
            
            if (result.status === 'success') {
                const validation = result.data;
                if (validation.is_valid) {
                    AutoShift.Alert.success('シフトは有効です');
                } else {
                    AutoShift.Alert.warning(`${validation.violation_count}件の制約違反があります`);
                }
                return validation;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            AutoShift.Alert.error(`シフト検証に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * シフトエクスポート
     */
    export: async (month, format) => {
        try {
            const url = AutoShift.API.endpoints.shift.export(month, format);
            const link = document.createElement('a');
            link.href = url;
            link.download = `shift_${month}.${format}`;
            link.click();
            
            AutoShift.Alert.success(`${format.toUpperCase()}形式でエクスポートを開始しました`);
        } catch (error) {
            AutoShift.Alert.error(`エクスポートに失敗しました: ${error.message}`);
            throw error;
        }
    }
};

// ====================
// ルール管理API
// ====================

AutoShift.RuleAPI = {
    /**
     * ルール一覧取得
     */
    getRules: async () => {
        try {
            const result = await AutoShift.API.get(AutoShift.API.endpoints.rules.facility);
            return result.data;
        } catch (error) {
            AutoShift.Alert.error(`ルール取得に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * ルール作成
     */
    createRule: async (ruleData) => {
        try {
            const result = await AutoShift.API.post(AutoShift.API.endpoints.rules.facility, ruleData);
            
            if (result.status === 'success') {
                AutoShift.Alert.success(`ルール「${ruleData.rule_name}」を作成しました`);
                return result.data;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            AutoShift.Alert.error(`ルール作成に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * ルール更新
     */
    updateRule: async (ruleId, ruleData) => {
        try {
            const result = await AutoShift.API.put(AutoShift.API.endpoints.rules.facilityById(ruleId), ruleData);
            
            if (result.status === 'success') {
                AutoShift.Alert.success(`ルール「${ruleId}」を更新しました`);
                return result.data;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            AutoShift.Alert.error(`ルール更新に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * ルール削除
     */
    deleteRule: async (ruleId) => {
        try {
            const confirmed = await new Promise((resolve) => {
                AutoShift.Modal.confirm(
                    `ルール「${ruleId}」を削除しますか？この操作は取り消せません。`,
                    () => resolve(true),
                    () => resolve(false)
                );
            });

            if (!confirmed) return;

            const result = await AutoShift.API.delete(AutoShift.API.endpoints.rules.facilityById(ruleId));
            
            if (result.status === 'success') {
                AutoShift.Alert.success(`ルール「${ruleId}」を削除しました`);
                return true;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            AutoShift.Alert.error(`ルール削除に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * ルール検証
     */
    validateRule: async (ruleDefinition) => {
        try {
            const result = await AutoShift.API.post(AutoShift.API.endpoints.rules.validate, {
                rule_definition: ruleDefinition
            });
            
            if (result.status === 'success') {
                AutoShift.Alert.success('ルール定義は有効です');
                return true;
            } else {
                AutoShift.Alert.error(`ルール検証エラー: ${result.errors?.join(', ')}`);
                return false;
            }
        } catch (error) {
            AutoShift.Alert.error(`ルール検証に失敗しました: ${error.message}`);
            throw error;
        }
    }
};

// ====================
// 希望休管理API
// ====================

AutoShift.HolidayAPI = {
    /**
     * スタッフ一覧取得
     */
    getStaff: async () => {
        try {
            const result = await AutoShift.API.get(AutoShift.API.endpoints.holidays.staff);
            return result.data;
        } catch (error) {
            AutoShift.Alert.error(`スタッフ一覧取得に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * 希望休一覧取得
     */
    getHolidays: async (month) => {
        try {
            const result = await AutoShift.API.get(AutoShift.API.endpoints.holidays.request(month));
            return result.data;
        } catch (error) {
            AutoShift.Alert.error(`希望休取得に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * 希望休追加
     */
    addHoliday: async (month, holidayData) => {
        try {
            const result = await AutoShift.API.post(
                AutoShift.API.endpoints.holidays.request(month), 
                holidayData
            );
            
            if (result.status === 'success') {
                AutoShift.Alert.success(result.message);
                return result.data;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            AutoShift.Alert.error(`希望休登録に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * 希望休削除
     */
    deleteHoliday: async (month, staffId, date) => {
        try {
            const result = await AutoShift.API.delete(
                AutoShift.API.endpoints.holidays.requestById(month, staffId, date)
            );
            
            if (result.status === 'success') {
                AutoShift.Alert.success(result.message);
                return true;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            AutoShift.Alert.error(`希望休削除に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * 希望休一括登録
     */
    bulkAddHolidays: async (month, holidaysData) => {
        try {
            const result = await AutoShift.API.post(
                AutoShift.API.endpoints.holidays.bulk(month),
                { requests: holidaysData }
            );
            
            if (result.status === 'success') {
                AutoShift.Alert.success(result.message);
                return result.data;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            AutoShift.Alert.error(`一括登録に失敗しました: ${error.message}`);
            throw error;
        }
    },

    /**
     * カレンダーデータ取得
     */
    getCalendarData: async (month) => {
        try {
            const result = await AutoShift.API.get(AutoShift.API.endpoints.holidays.calendar(month));
            return result.data;
        } catch (error) {
            AutoShift.Alert.error(`カレンダーデータ取得に失敗しました: ${error.message}`);
            throw error;
        }
    }
};

// ====================
// データキャッシュ管理
// ====================

AutoShift.Cache = {
    data: new Map(),
    expiry: new Map(),

    /**
     * データ設定（TTL付き）
     */
    set: (key, value, ttl = 300000) => { // 5分デフォルト
        AutoShift.Cache.data.set(key, value);
        AutoShift.Cache.expiry.set(key, Date.now() + ttl);
    },

    /**
     * データ取得
     */
    get: (key) => {
        const expiry = AutoShift.Cache.expiry.get(key);
        if (expiry && Date.now() > expiry) {
            AutoShift.Cache.delete(key);
            return undefined;
        }
        return AutoShift.Cache.data.get(key);
    },

    /**
     * データ削除
     */
    delete: (key) => {
        AutoShift.Cache.data.delete(key);
        AutoShift.Cache.expiry.delete(key);
    },

    /**
     * キャッシュクリア
     */
    clear: () => {
        AutoShift.Cache.data.clear();
        AutoShift.Cache.expiry.clear();
    },

    /**
     * 期限切れキャッシュ削除
     */
    cleanup: () => {
        const now = Date.now();
        for (const [key, expiry] of AutoShift.Cache.expiry) {
            if (now > expiry) {
                AutoShift.Cache.delete(key);
            }
        }
    }
};

// ====================
// データ取得ヘルパー（キャッシュ付き）
// ====================

AutoShift.Data = {
    /**
     * スタッフ一覧取得（キャッシュ付き）
     */
    getStaff: async (useCache = true) => {
        const cacheKey = 'staff_list';
        
        if (useCache) {
            const cached = AutoShift.Cache.get(cacheKey);
            if (cached) return cached;
        }
        
        const staff = await AutoShift.HolidayAPI.getStaff();
        AutoShift.Cache.set(cacheKey, staff);
        return staff;
    },

    /**
     * ルール一覧取得（キャッシュ付き）
     */
    getRules: async (useCache = true) => {
        const cacheKey = 'rules_list';
        
        if (useCache) {
            const cached = AutoShift.Cache.get(cacheKey);
            if (cached) return cached;
        }
        
        const rules = await AutoShift.RuleAPI.getRules();
        AutoShift.Cache.set(cacheKey, rules);
        return rules;
    },

    /**
     * 希望休データ取得（キャッシュ付き）
     */
    getHolidays: async (month, useCache = true) => {
        const cacheKey = `holidays_${month}`;
        
        if (useCache) {
            const cached = AutoShift.Cache.get(cacheKey);
            if (cached) return cached;
        }
        
        const holidays = await AutoShift.HolidayAPI.getHolidays(month);
        AutoShift.Cache.set(cacheKey, holidays);
        return holidays;
    },

    /**
     * キャッシュ無効化
     */
    invalidateCache: (pattern) => {
        if (pattern) {
            for (const key of AutoShift.Cache.data.keys()) {
                if (key.includes(pattern)) {
                    AutoShift.Cache.delete(key);
                }
            }
        } else {
            AutoShift.Cache.clear();
        }
    }
};

// ====================
// 自動キャッシュクリーンアップ
// ====================

// 5分ごとに期限切れキャッシュを削除
setInterval(() => {
    AutoShift.Cache.cleanup();
}, 300000);

// ====================
// エラーハンドリング
// ====================

// グローバルエラーハンドラー
window.addEventListener('unhandledrejection', (event) => {
    console.error('未処理のPromise拒否:', event.reason);
    AutoShift.Alert.error('予期しないエラーが発生しました');
});

// ====================
// パフォーマンス監視
// ====================

AutoShift.Performance = {
    /**
     * API呼び出し時間計測
     */
    measureAPICall: async (apiFunction, ...args) => {
        const start = performance.now();
        try {
            const result = await apiFunction(...args);
            const end = performance.now();
            console.log(`API呼び出し時間: ${end - start}ms`);
            return result;
        } catch (error) {
            const end = performance.now();
            console.error(`API呼び出しエラー (${end - start}ms):`, error);
            throw error;
        }
    },

    /**
     * DOM操作時間計測
     */
    measureDOMOperation: (operation, description) => {
        const start = performance.now();
        const result = operation();
        const end = performance.now();
        console.log(`DOM操作「${description}」: ${end - start}ms`);
        return result;
    }
};

console.log('AutoShift API JavaScript ロード完了');