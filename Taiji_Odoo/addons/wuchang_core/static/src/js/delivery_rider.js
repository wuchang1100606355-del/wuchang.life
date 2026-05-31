/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class DeliveryRiderInterface extends Component {
    setup() {
        this.state = useState({
            is_online: false,
            checks: {
                helmet: false,
                bag: false,
                vest: false,
                phone: false,
                all_checked: false
            },
            order: { name: 'W001' } // Dummy data
        });
    }

    get allChecked() {
        const c = this.state.checks;
        return c.helmet && c.bag && c.vest && c.phone;
    }

    async goOnline() {
        if (!this.allChecked) return;
        // Call backend to verify or log status
        // await this.env.services.rpc('/wuchang/rider/online', { ... });
        this.state.is_online = true;
    }

    openSettings() {
        // Navigate to settings or show modal
        console.log("Open settings");
    }
}
DeliveryRiderInterface.template = "DeliveryRiderInterface";

// Register the component
registry.category("actions").add("wuchang_delivery_rider", DeliveryRiderInterface);
