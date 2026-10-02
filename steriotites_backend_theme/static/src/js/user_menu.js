/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { registry } from "@web/core/registry";

const userMenuRegistry = registry.category("user_menuitems");

// Unregister target items directly from userMenuRegistry
const KEYS_TO_REMOVE = [
    "support",       // Help
    "odoo_account",  // My Odoo.com Account
    "install_pwa",   // Install App
    "im_status",     // Offline / IM status
];

for (const key of KEYS_TO_REMOVE) {
    if (userMenuRegistry.contains(key)) {
        userMenuRegistry.remove(key);
    }
}

// Element IDs to filter out in case items are injected dynamically
const HIDDEN_ITEM_IDS = new Set([
    "support",
    "account",       // odooAccountItem uses id: "account"
    "odoo_account",
    "install_pwa",
]);

patch(UserMenu.prototype, {
    getElements() {
        const elements = super.getElements();
        const filtered = elements.filter((el) => {
            if (!el) {
                return false;
            }
            if (el.id && HIDDEN_ITEM_IDS.has(el.id)) {
                return false;
            }
            if (
                el.type === "component" &&
                (el.contentComponent?.name === "ImStatusDropdown" || el.id === "im_status")
            ) {
                return false;
            }
            return true;
        });

        // Clean up redundant / leading / trailing / consecutive separators
        const result = [];
        for (let i = 0; i < filtered.length; i++) {
            const item = filtered[i];
            if (item.type === "separator") {
                if (result.length === 0 || result[result.length - 1].type === "separator") {
                    continue;
                }
                const hasNext = filtered.slice(i + 1).some((next) => next.type !== "separator");
                if (!hasNext) {
                    continue;
                }
            }
            result.push(item);
        }
        return result;
    },
});
