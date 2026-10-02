/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { user } from "@web/core/user";
import { useService, useBus } from "@web/core/utils/hooks";
import { proxy } from "@odoo/owl";

/** Only this app shows expandable sidebar submenus. */
const SIDEBAR_TREE_APP_XMLIDS = new Set([
    "stakeholder_registration.menu_stakeholder_registration_root",
]);

patch(WebClient.prototype, {
    setup() {
        super.setup();

        this.ui = proxy(useService("ui"));
        this.user = user;

        this.state.sidebarOpen = false;
        this.state.sidebarMini = false;
        this.state.allAppsOpen = true;
        this.state.currentAppSections = [];
        this.state.activeMenuId = null;
        this.state.expandedAppIds = {};
        this._updateCurrentAppSections();

        this.state.currentAppId = this.menuService.getCurrentApp()?.id;
        const currentApp = this.menuService.getCurrentApp();
        if (currentApp && this.isSidebarTreeApp(currentApp) && this.state.currentAppSections.length) {
            this._setAppExpanded(currentApp.id, true);
        }

        useBus(this.env.bus, "MENUS:APP-CHANGED", this._onMenuChanged.bind(this));
    },

    toggleSidebar() {
        this.state.sidebarOpen = !this.state.sidebarOpen;
    },

    toggleMiniSidebar() {
        this.state.sidebarMini = !this.state.sidebarMini;
    },

    toggleAllAppsOpen() {
        this.state.allAppsOpen = !this.state.allAppsOpen;
    },

    isSidebarTreeApp(app) {
        return !!(app && SIDEBAR_TREE_APP_XMLIDS.has(app.xmlid));
    },

    isAppExpanded(appId) {
        return !!this.state.expandedAppIds[appId];
    },

    _setAppExpanded(appId, expanded) {
        this.state.expandedAppIds = {
            ...this.state.expandedAppIds,
            [appId]: expanded,
        };
    },

    getAppSections(app) {
        if (!app || !this.isSidebarTreeApp(app)) {
            return [];
        }
        const tree = this.menuService.getMenuAsTree(app.id);
        return tree?.childrenTree || [];
    },

    _updateCurrentAppSections() {
        const currentApp = this.menuService.getCurrentApp();
        if (!currentApp) {
            this.state.currentAppSections = [];
            return;
        }
        const tree = this.menuService.getMenuAsTree(currentApp.id);
        this.state.currentAppSections = tree?.childrenTree || [];
    },

    _onMenuChanged() {
        const currentApp = this.menuService.getCurrentApp();
        this.state.currentAppId = currentApp?.id || null;
        this._updateCurrentAppSections();
        if (
            currentApp &&
            this.isSidebarTreeApp(currentApp) &&
            this.state.currentAppSections.length
        ) {
            this._setAppExpanded(currentApp.id, true);
        }
    },

    onAppClick(app) {
        if (!app) {
            return;
        }

        // Only Eco System Partners uses sidebar expand/collapse.
        if (this.isSidebarTreeApp(app)) {
            const sections = this.getAppSections(app);
            if (sections.length) {
                if (this.state.currentAppId === app.id) {
                    this._setAppExpanded(app.id, !this.isAppExpanded(app.id));
                    return;
                }
                this._setAppExpanded(app.id, true);
            }
        }

        this.onSidebarMenuSelection(app);
    },

    onSidebarMenuSelection(menu, close = false) {
        if (!menu) {
            return;
        }

        const actionableMenu = this._findFirstActionMenu(menu);
        if (!actionableMenu) {
            return;
        }

        this.state.activeMenuId = actionableMenu.id;
        this.menuService.selectMenu(actionableMenu);

        if (actionableMenu.appID) {
            this.menuService.setCurrentMenu(actionableMenu.appID);
            if (close) {
                this.state.sidebarOpen = false;
            }
        }
    },

    _findFirstActionMenu(menu) {
        if (menu.actionID) {
            return menu;
        }
        if (!menu.childrenTree) {
            return null;
        }
        for (const child of menu.childrenTree) {
            const found = this._findFirstActionMenu(child);
            if (found) {
                return found;
            }
        }
        return null;
    },

    _getMenuIcon(menu) {
        if (menu.webIconData) {
            return menu.webIconData;
        }
        if (menu.webIcon && typeof menu.webIcon === "string") {
            const parts = menu.webIcon.split(",");
            if (parts.length === 2 && parts[1].includes("/")) {
                return `/${parts[0].trim()}/${parts[1].trim()}`;
            }
        }
        return "/web/static/img/menu_icon.svg";
    },
});
