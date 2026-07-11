class BtnCellRenderer {
    init(params) {
        this.params = params;
        this.eGui = document.createElement('div');
        this.eGui.style.position = 'relative';  // To position elements within the cell
        if (String(this.params.value).includes('[clicked]')) {
            this.params.value = this.params.value.replace('[clicked]','');
            this.params.originalValue = this.params.value;
            this.makeButton('📍');
        } else {
            this.params.originalValue = this.params.value;
            this.makeButton('🔍');
        }
    }

    makeButton(symbol) {
        this.destroy();
        this.eGui.innerHTML = `
            <span id='click-button' style="position: absolute; left: 0; top: 50%; transform: translateY(-50%);">
                ${symbol}
            </span>
            <span style="margin-left: 24px;">${this.params.value}</span>`;
        this.eButton = this.eGui.querySelector('#click-button');
        this.btnClickedHandler = this.btnClickedHandler.bind(this);
        this.eButton.addEventListener('click', this.btnClickedHandler);
    }

    getGui() { return this.eGui; }

    refresh() { return true; }

    destroy() {
        if (this.eButton) { this.eGui.removeEventListener('click', this.btnClickedHandler); }
    }

    refreshTable(value) { this.params.setValue(value); }

    btnClickedHandler(event) {
        if(String(this.params.getValue()).includes('[clicked]')) {
            this.refreshTable(this.params.originalValue);
            this.makeButton('🔍');
        } else {
            this.refreshTable('[clicked]'+this.params.originalValue);
            this.makeButton('📍');
        }
    }
};

// export class RescheduleButtonRenderer {

//     init(params) {
//         this.params = params;
//         this.eGui = document.createElement('div');
//         const eButton = document.createElement('button');
//         eButton.className = 'btn-simple';
//         eButton.textContent = 'Reschedule';

//         this.btnClickedHandler = this.btnClickedHandler.bind(this);
//         eButton.addEventListener('click', this.btnClickedHandler);
        
//         this.eGui.appendChild(eButton);


//     }

//     getGui() {
//         return this.eGui;
//     }

//     refresh() {
//         return true;
//     }

//     destroy() {
//         if (this.eButton) {
//             this.eButton.removeEventListener('click', this.btnClickedHandler);
//         }
//     }

//     btnClickedHandler(event) {
//         // confirm('Row data: ' + JSON.stringify(this.params.node.data) + '\n\nDo you want to reschedule?');
//         setTriggerValue('clicked', this.params.node.data);
//     }
// }