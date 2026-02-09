/**
 * AutoShift - グリッド・テーブル・UI操作JavaScript
 * 2026年2月9日
 */

// グローバル変数
window.AutoShift = window.AutoShift || {};

// ====================
// ユーティリティ関数
// ====================

AutoShift.Utils = {
    /**
     * 日付フォーマット（YYYY-MM-DD形式）
     */
    formatDate: (date) => {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    },

    /**
     * 時間フォーマット（HH:MM形式）
     */
    formatTime: (date) => {
        if (typeof date === 'string') {
            date = new Date(date);
        }
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    },

    /**
     * 日付時刻フォーマット
     */
    formatDateTime: (date) => {
        return `${AutoShift.Utils.formatDate(date)} ${AutoShift.Utils.formatTime(date)}`;
    },

    /**
     * 数値フォーマット（3桁区切り）
     */
    formatNumber: (num) => {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },

    /**
     * 文字列のエスケープ処理
     */
    escapeHtml: (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * デバウンス処理
     */
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * アニメーション付きスムーズスクロール
     */
    smoothScrollTo: (element) => {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
};

// ====================
// アラート・通知システム
// ====================

AutoShift.Alert = {
    container: null,

    /**
     * アラートコンテナ初期化
     */
    init: () => {
        AutoShift.Alert.container = document.getElementById('alert-area') || 
                                   AutoShift.Alert.createContainer();
    },

    /**
     * アラートコンテナ作成
     */
    createContainer: () => {
        const container = document.createElement('div');
        container.id = 'alert-area';
        container.className = 'alert-container';
        document.body.insertBefore(container, document.body.firstChild);
        return container;
    },

    /**
     * アラート表示
     */
    show: (type, message, duration = 5000) => {
        if (!AutoShift.Alert.container) {
            AutoShift.Alert.init();
        }

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.innerHTML = `
            <span>${AutoShift.Utils.escapeHtml(message)}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">×</button>
        `;

        // 既存のアラートをクリア
        AutoShift.Alert.container.innerHTML = '';
        AutoShift.Alert.container.appendChild(alertDiv);

        // フェードイン
        setTimeout(() => {
            alertDiv.style.opacity = '1';
        }, 50);

        // 自動削除
        if (duration > 0) {
            setTimeout(() => {
                AutoShift.Alert.fadeOut(alertDiv);
            }, duration);
        }
    },

    /**
     * アラートフェードアウト
     */
    fadeOut: (element) => {
        element.style.opacity = '0';
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }, 300);
    },

    /**
     * 成功アラート
     */
    success: (message, duration) => {
        AutoShift.Alert.show('success', message, duration);
    },

    /**
     * エラーアラート
     */
    error: (message, duration) => {
        AutoShift.Alert.show('error', message, duration);
    },

    /**
     * 警告アラート
     */
    warning: (message, duration) => {
        AutoShift.Alert.show('warning', message, duration);
    },

    /**
     * 情報アラート
     */
    info: (message, duration) => {
        AutoShift.Alert.show('info', message, duration);
    }
};

// ====================
// テーブル・グリッド
// ====================

AutoShift.Grid = {
    /**
     * ソート可能テーブル初期化
     */
    initSortableTable: (tableId) => {
        const table = document.getElementById(tableId);
        if (!table) return;

        const headers = table.querySelectorAll('th[data-sort]');
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                AutoShift.Grid.sortTable(table, header.dataset.sort);
            });

            // ソートアイコン追加
            if (!header.querySelector('.sort-icon')) {
                const icon = document.createElement('span');
                icon.className = 'sort-icon';
                icon.innerHTML = ' ↕️';
                header.appendChild(icon);
            }
        });
    },

    /**
     * テーブルソート処理
     */
    sortTable: (table, column) => {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // 現在のソート状態を確認
        const currentSort = table.dataset.sort;
        const isAscending = currentSort !== column || table.dataset.sortDir === 'desc';
        
        // データソート
        const sortedRows = rows.sort((a, b) => {
            const aValue = a.dataset[column] || a.cells[0].textContent;
            const bValue = b.dataset[column] || b.cells[0].textContent;
            
            // 数値判定
            const aNum = parseFloat(aValue);
            const bNum = parseFloat(bValue);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAscending ? aNum - bNum : bNum - aNum;
            }
            
            // 文字列ソート
            return isAscending ? 
                aValue.localeCompare(bValue) : 
                bValue.localeCompare(aValue);
        });

        // テーブル更新
        tbody.innerHTML = '';
        sortedRows.forEach(row => tbody.appendChild(row));

        // ソート状態保存
        table.dataset.sort = column;
        table.dataset.sortDir = isAscending ? 'asc' : 'desc';

        // ソートアイコン更新
        table.querySelectorAll('.sort-icon').forEach(icon => {
            icon.innerHTML = ' ↕️';
        });
        
        const currentIcon = table.querySelector(`th[data-sort="${column}"] .sort-icon`);
        if (currentIcon) {
            currentIcon.innerHTML = isAscending ? ' ↑' : ' ↓';
        }
    },

    /**
     * テーブル検索機能
     */
    initTableSearch: (searchInputId, tableId, searchColumns = []) => {
        const searchInput = document.getElementById(searchInputId);
        const table = document.getElementById(tableId);
        
        if (!searchInput || !table) return;

        const searchHandler = AutoShift.Utils.debounce((query) => {
            const tbody = table.querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');
            
            query = query.toLowerCase().trim();
            
            rows.forEach(row => {
                let matchFound = false;
                
                if (searchColumns.length === 0) {
                    // 全列検索
                    matchFound = row.textContent.toLowerCase().includes(query);
                } else {
                    // 指定列検索
                    searchColumns.forEach(colIndex => {
                        if (row.cells[colIndex] && 
                            row.cells[colIndex].textContent.toLowerCase().includes(query)) {
                            matchFound = true;
                        }
                    });
                }
                
                row.style.display = matchFound || query === '' ? '' : 'none';
            });

            // 検索結果カウント表示
            const visibleRows = tbody.querySelectorAll('tr:not([style*="none"])').length;
            const totalRows = rows.length;
            
            AutoShift.Grid.showSearchResults(visibleRows, totalRows, query);
        }, 300);

        searchInput.addEventListener('input', (e) => {
            searchHandler(e.target.value);
        });
    },

    /**
     * 検索結果表示
     */
    showSearchResults: (visible, total, query) => {
        let resultDiv = document.getElementById('search-results');
        if (!resultDiv) {
            resultDiv = document.createElement('div');
            resultDiv.id = 'search-results';
            resultDiv.className = 'search-results text-muted';
            const searchInput = document.querySelector('input[type="search"], input[placeholder*="検索"]');
            if (searchInput && searchInput.parentNode) {
                searchInput.parentNode.insertBefore(resultDiv, searchInput.nextSibling);
            }
        }

        if (query.trim() === '') {
            resultDiv.textContent = '';
        } else {
            resultDiv.textContent = `${total}件中 ${visible}件を表示`;
        }
    },

    /**
     * 行選択機能
     */
    initRowSelection: (tableId) => {
        const table = document.getElementById(tableId);
        if (!table) return;

        const tbody = table.querySelector('tbody');
        tbody.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            if (!row) return;

            // Ctrl/Cmdキー押下で複数選択
            if (!e.ctrlKey && !e.metaKey) {
                // 単一選択
                tbody.querySelectorAll('tr.selected').forEach(r => {
                    r.classList.remove('selected');
                });
            }

            row.classList.toggle('selected');
            AutoShift.Grid.updateSelectionInfo(table);
        });
    },

    /**
     * 選択情報更新
     */
    updateSelectionInfo: (table) => {
        const selectedRows = table.querySelectorAll('tbody tr.selected');
        const event = new CustomEvent('selectionChange', {
            detail: {
                selectedRows: selectedRows,
                count: selectedRows.length
            }
        });
        table.dispatchEvent(event);
    }
};

// ====================
// モーダル管理
// ====================

AutoShift.Modal = {
    /**
     * モーダル表示
     */
    show: (modalId) => {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.classList.add('show');
        modal.style.display = 'flex';
        
        // フォーカス管理
        const firstInput = modal.querySelector('input, select, textarea, button');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }

        // Escapeキーで閉じる
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                AutoShift.Modal.hide(modalId);
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);

        // 背景クリックで閉じる
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                AutoShift.Modal.hide(modalId);
            }
        });
    },

    /**
     * モーダル非表示
     */
    hide: (modalId) => {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    },

    /**
     * 確認ダイアログ
     */
    confirm: (message, onConfirm, onCancel) => {
        if (window.confirm(message)) {
            if (onConfirm) onConfirm();
        } else {
            if (onCancel) onCancel();
        }
    }
};

// ====================
// フォーム管理
// ====================

AutoShift.Form = {
    /**
     * フォーム検証
     */
    validate: (formId, rules = {}) => {
        const form = document.getElementById(formId);
        if (!form) return false;

        let isValid = true;
        const errors = [];

        // HTML5バリデーション
        if (!form.checkValidity()) {
            isValid = false;
            const invalidElements = form.querySelectorAll(':invalid');
            invalidElements.forEach(element => {
                errors.push(`${element.name || 'フィールド'}: ${element.validationMessage}`);
            });
        }

        // カスタムルール検証
        Object.keys(rules).forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            const rule = rules[fieldName];
            
            if (field && rule.required && !field.value.trim()) {
                isValid = false;
                errors.push(`${rule.label || fieldName}は必須です`);
            }
            
            if (field && rule.pattern && !rule.pattern.test(field.value)) {
                isValid = false;
                errors.push(`${rule.label || fieldName}の形式が正しくありません`);
            }
        });

        // エラー表示
        if (!isValid) {
            AutoShift.Alert.error(`入力エラー:\n${errors.join('\n')}`);
        }

        return isValid;
    },

    /**
     * フォームデータ取得
     */
    getData: (formId) => {
        const form = document.getElementById(formId);
        if (!form) return {};

        const formData = new FormData(form);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            // チェックボックスの場合は配列として処理
            if (form.querySelector(`[name="${key}"][type="checkbox"]`)) {
                if (!data[key]) data[key] = [];
                data[key].push(value);
            } else {
                data[key] = value;
            }
        }

        return data;
    },

    /**
     * フォームリセット
     */
    reset: (formId) => {
        const form = document.getElementById(formId);
        if (form) {
            form.reset();
            // カスタムクラス削除
            form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
                el.classList.remove('is-invalid', 'is-valid');
            });
        }
    }
};

// ====================
// API呼び出し
// ====================

AutoShift.API = {
    /**
     * 基本API呼び出し
     */
    call: async (url, options = {}) => {
        const defaults = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        };

        const config = { ...defaults, ...options };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || '通信エラーが発生しました');
            }
            
            return data;
        } catch (error) {
            console.error('API呼び出しエラー:', error);
            throw error;
        }
    },

    /**
     * GET リクエスト
     */
    get: async (url) => {
        return AutoShift.API.call(url);
    },

    /**
     * POST リクエスト
     */
    post: async (url, data) => {
        return AutoShift.API.call(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    /**
     * PUT リクエスト
     */
    put: async (url, data) => {
        return AutoShift.API.call(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    /**
     * DELETE リクエスト
     */
    delete: async (url) => {
        return AutoShift.API.call(url, {
            method: 'DELETE'
        });
    }
};

// ====================
// ページ初期化
// ====================

AutoShift.init = () => {
    // アラートシステム初期化
    AutoShift.Alert.init();
    
    // ソート可能テーブル初期化
    document.querySelectorAll('table[data-sortable]').forEach(table => {
        AutoShift.Grid.initSortableTable(table.id);
    });
    
    // 検索機能初期化
    document.querySelectorAll('[data-search-target]').forEach(input => {
        const targetTable = input.dataset.searchTarget;
        AutoShift.Grid.initTableSearch(input.id, targetTable);
    });
    
    // 行選択機能初期化
    document.querySelectorAll('table[data-row-selection]').forEach(table => {
        AutoShift.Grid.initRowSelection(table.id);
    });
    
    // モーダルクローズボタン設定
    document.querySelectorAll('[data-modal-close]').forEach(button => {
        button.addEventListener('click', (e) => {
            const modalId = button.dataset.modalClose;
            AutoShift.Modal.hide(modalId);
        });
    });
    
    console.log('AutoShift JavaScript初期化完了');
};

// DOM読み込み完了時に初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', AutoShift.init);
} else {
    AutoShift.init();
}