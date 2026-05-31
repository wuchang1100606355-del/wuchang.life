/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount, useRef, xml } from "@odoo/owl";
import CommunitySuperApp from "./community_super_app.jsx";

// Since we are in an Odoo environment, we need to bridge React and OWL/Odoo.
// We will use a wrapper component that renders the React app into a ref.
// Note: We need a way to render React. Since we are using JSX in .jsx files,
// we assume the build system handles it. However, in standard Odoo, we might
// need 'react' and 'react-dom/client' available globally or bundled.
// For this environment, we assume 'react' and 'react-dom/client' are available via global variable or import map
// If not, we would need to add them to the assets.
// Assuming standard Odoo 16+ structure where we can import if mapped.
// If direct import fails in browser, we might need a different approach (e.g. dynamic import or global React).

import React from "react";
import { createRoot } from "react-dom/client";

class CommunitySuperAppClientAction extends Component {
    static template = xml`
        <div class="o_community_super_app h-100" t-ref="root"></div>
    `;

    setup() {
        this.rootRef = useRef("root");
        this.reactRoot = null;

        onMounted(() => {
            if (this.rootRef.el) {
                this.reactRoot = createRoot(this.rootRef.el);
                this.reactRoot.render(React.createElement(CommunitySuperApp));
            }
        });

        onWillUnmount(() => {
            if (this.reactRoot) {
                this.reactRoot.unmount();
            }
        });
    }
}

registry.category("actions").add("wuchang_core.community_super_app_action", CommunitySuperAppClientAction);
