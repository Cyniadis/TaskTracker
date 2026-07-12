class FrequencyCellEditor {
    init(params) {
        this.params = params;
        this.value = String(params.value || '1xjour');
        this.eGui = document.createElement('div');
        this.eGui.style.display = 'flex';
        this.eGui.style.alignItems = 'center';
        this.eGui.style.gap = '6px';
        this.eGui.style.padding = '2px';
        this.eGui.style.width = '180px';

        const parsed = this._parseValue(this.value);

        this.numberInput = document.createElement('input');
        this.numberInput.type = 'number';
        this.numberInput.min = '1';
        this.numberInput.step = '1';
        this.numberInput.value = parsed.number;
        this.numberInput.style.width = '70px';

        this.separator = document.createElement('span');
        this.separator.textContent = 'x';
        this.separator.style.fontWeight = 'bold';

        this.periodSelect = document.createElement('select');
        this.periodSelect.style.width = '100px';
        const periods = ['jour', 'semaine', 'mois', 'an'];
        for (const period of periods) {
            const option = document.createElement('option');
            option.value = period;
            option.textContent = period;
            if (period === parsed.period) {
                option.selected = true;
            }
            this.periodSelect.appendChild(option);
        }

        this.eGui.appendChild(this.numberInput);
        this.eGui.appendChild(this.separator);
        this.eGui.appendChild(this.periodSelect);
    }

    _parseValue(value) {
        const match = String(value || '1xjour').match(/^\s*(\d+)\s*x\s*([a-zA-Z]+)\s*$/i);
        if (match) {
            return {
                number: match[1],
                period: match[2].toLowerCase(),
            };
        }
        return {
            number: '1',
            period: 'jour',
        };
    }

    afterGuiAttached() {
        this.numberInput.focus();
        this.numberInput.select();
    }

    getGui() {
        return this.eGui;
    }

    getValue() {
        const number = parseInt(this.numberInput.value || '1', 10);
        const safeNumber = Number.isNaN(number) || number < 1 ? 1 : number;
        return `${safeNumber}x${this.periodSelect.value}`;
    }

    isPopup() {
        return true;
    }

    destroy() {
        this.eGui = null;
    }
}
