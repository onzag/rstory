import schema from '../schema/character.js';
import { character, party, world, utils } from '../schema/variables.js';

function escapeHTML(str) {
    return str.replace(/[&<>"']/g, function(match) {
        const escapeMap = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        };
        return escapeMap[match];
    });
}

const WIZARD_SECTIONS = [
    {
        title: "Basic Information",
        fields: [
            "Character Overview",
            [
                "name",
                "group",
                "gender",
                "sex",
                "general",
                "short"
            ],
            "Initiative",
            [
                
            ]
        ]
    }
]

// Sound effects
const hoverSound = document.getElementById('hoverSound');
const confirmSound = document.getElementById('confirmSound');
const cancelSound = document.getElementById('cancelSound');
const pauseSound = document.getElementById('pauseSound');

function playHoverSound() {
  hoverSound.currentTime = 0;
  hoverSound.play().catch(err => console.log('Hover sound play failed:', err));
}

function playConfirmSound() {
  confirmSound.currentTime = 0;
  confirmSound.play().catch(err => console.log('Confirm sound play failed:', err));
}

function playCancelSound() {
  cancelSound.currentTime = 0;
  cancelSound.play().catch(err => console.log('Cancel sound play failed:', err));
}

function playPauseSound() {
  pauseSound.currentTime = 0;
  pauseSound.play().catch(err => console.log('Pause sound play failed:', err));
}

class CharacterOverlay extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });

        this.currentSectionIndex = 0;
    }

    connectedCallback() {
        this.currentCharacterGroup = this.getAttribute("character-group") || "default";
        this.currentCharacterFile = this.getAttribute("character-file") || null;

        this.lastSavedCharacterGroup = this.currentCharacterGroup;
        this.lastSavedCharacterFile = this.currentCharacterFile;
        this.currentCharacterName = "";

        window.electronAPI.loadStringFromUserData("name", this.currentCharacterGroup, this.currentCharacterFile).then((name) => {
            if (name) {
                this.currentCharacterName = name;
            } else {
                this.currentCharacterName = "Unnamed Character";
            }
            this.shadowRoot.querySelector('app-overlay').setAttribute("overlay-title", `Working on: ${JSON.stringify(escapeHTML(this.currentCharacterName))}`);
        });

        this.render();
        playPauseSound();
        this.buildChildrenMap();
        this.shadowRoot.querySelector('app-overlay').addEventListener('special-button-click', () => {
            const dialog = document.createElement('app-dialog');
            dialog.setAttribute('dialog-title', 'Character Creation Help');
            dialog.innerHTML = `
                <p>The character creator uses handlebars for templating.</p>
                <p>For more information on how to use it, please visit <a href="https://handlebarsjs.com/" target="_blank">the official Handlebars website</a>.</p>
                <p>Available values for templating are the following:</p>
                <h3>Character Variables</h3>
                <table>
                <thead>
                    <tr><th>Variable</th><th>Description</th></tr>
                    </thead>
                    <tbody>
                    ${character.map(varInfo => `<tr title=${JSON.stringify(escapeHTML(varInfo[2]))}><td>{{${varInfo[0]}}}</td><td>${escapeHTML(varInfo[1])}</td></tr>`).join('')}
                </tbody>
                </table>
                <h3>Party Variables</h3>
                <table>
                    <thead>
                    <tr><th>Variable</th><th>Description</th></tr>
                    </thead>
                    <tbody>
                    ${party.map(varInfo => `<tr title=${JSON.stringify(escapeHTML(varInfo[2]))}><td>{{${varInfo[0]}}}</td><td>${escapeHTML(varInfo[1])}</td></tr>`).join('')}
                </tbody>
                </table>
                <h3>World Variables</h3>
                <table>
                <thead>
                    <tr><th>Variable</th><th>Description</th></tr>
                    </thead>
                    <tbody>
                    ${world.map(varInfo => `<tr title=${JSON.stringify(escapeHTML(varInfo[2]))}><td>{{${varInfo[0]}}}</td><td>${escapeHTML(varInfo[1])}</td></tr>`).join('')}
                </tbody>
                </table>
                <h3 Utility Functions</h3>
                <table>
                <thead>
                    <tr><th>Function</th><th>Description</th></tr>
                    </thead>
                    <tbody>
                    ${utils.map(funcInfo => `<tr title=${JSON.stringify(escapeHTML(funcInfo[2]))}><td>${funcInfo[0]}</td><td>${escapeHTML(funcInfo[1])}</td></tr>`).join('')}
                </tbody>
                </table>
            `;
            this.shadowRoot.appendChild(dialog);
            dialog.addEventListener('cancel', () => {
                this.shadowRoot.removeChild(dialog);
            });
        });
        this.shadowRoot.querySelector('app-overlay').addEventListener('confirm', () => {
            this.saveCurrent();
        });
        this.shadowRoot.querySelector('app-overlay').addEventListener('cancel', () => {
            this.dispatchEvent(new CustomEvent('close'));
            playConfirmSound();
        });
    }

    buildChildrenMap() {
        const sectionToDisplay = WIZARD_SECTIONS[this.currentSectionIndex];
        const fields = sectionToDisplay.fields;
        const fieldsAsHTML = fields.map(fieldName => {
            if (schema.properties[fieldName].type === "string") {
                if (schema.properties[fieldName].enum) {
                    // It's a select input
                    return `<app-overlay-select
                                class="${fieldName}"
                                label="${escapeHTML(schema.properties[fieldName].title)}" 
                                title="${escapeHTML(schema.properties[fieldName].description || '')}" 
                                input-data-location="${fieldName}"
                                input-data-character-group="${this.currentCharacterGroup}"
                                input-data-character-file="${this.currentCharacterFile}"
                                input-options='${JSON.stringify(schema.properties[fieldName].enum)}'>
                            </app-overlay-select>`;
                } else {
                    // It's a text input
                    const isMultiline = schema.properties[fieldName].multiline || false;
                    return `<app-overlay-input
                                class="${fieldName}"
                                label="${escapeHTML(schema.properties[fieldName].title)}" 
                                title="${escapeHTML(schema.properties[fieldName].description || '')}" 
                                input-data-location="${fieldName}"
                                input-data-character-group="${this.currentCharacterGroup}"
                                input-data-character-file="${this.currentCharacterFile}"
                                input-placeholder="${escapeHTML(schema.properties[fieldName].placeholder || '')}"
                                ${isMultiline ? 'multiline="true"' : ''}>
                            </app-overlay-input>`;
                }
            }
        }).join('');

        this.shadowRoot.querySelector('app-overlay').innerHTML = `<app-overlay-section section-title="${WIZARD_SECTIONS[this.currentSectionIndex].title}">${fieldsAsHTML}</app-overlay-section>`;

        if (this.currentSectionIndex === 0) {
            this.shadowRoot.querySelector('.name').shadowRoot.querySelector('input').addEventListener('input', (e) => {
                this.currentCharacterName = e.target.value;
                this.currentCharacterFile = e.target.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_') + ".json";
            });
            this.shadowRoot.querySelector('.group').shadowRoot.querySelector('input').addEventListener('input', (e) => {
                this.currentCharacterGroup = e.target.value;
            });
        }
    }

    async saveCurrent() {
        if (await window.electronAPI.checkCharacterFileExists(this.currentCharacterGroup.trim() || "default", this.currentCharacterFile)) {
            // Show overwrite dialog
            const dialog = document.createElement('app-dialog');
            dialog.setAttribute('dialog-title', 'A character with this name in that group already exists. Do you want to overwrite it?');
            dialog.setAttribute("confirmation", "true");
            dialog.setAttribute("confirm-text", "Overwrite");
            dialog.setAttribute("cancel-text", "Cancel");
            this.shadowRoot.appendChild(dialog);
            dialog.addEventListener('confirm', async () => {
                await this.updateCharacterFileOnDisk();
                this.shadowRoot.removeChild(dialog);
                playConfirmSound();
            });
            dialog.addEventListener('cancel', () => {
                this.shadowRoot.removeChild(dialog);
                playCancelSound();
            });
            this.shadowRoot.appendChild(dialog);
        } else {
            this.updateCharacterFileOnDisk();
            playConfirmSound();
        }
    }

    async updateCharacterFileOnDisk() {
        // save each field
        await Promise.all(Array.from(this.shadowRoot.querySelectorAll('app-overlay-input')).map(inputComponent => 
            inputComponent.saveValueToUserData()
        ));

        await Promise.all(Array.from(this.shadowRoot.querySelectorAll('app-overlay-select')).map(selectComponent => {
            return selectComponent.saveValueToUserData();
        }));
        
        await window.electronAPI.updateCharacterFileFromCache(
            this.lastSavedCharacterGroup.trim() || "default",
            this.lastSavedCharacterFile,
            this.currentCharacterFile
        ).then(() => {
            if ((this.lastSavedCharacterGroup.trim() || "default") !== (this.currentCharacterGroup.trim() || "default") || this.lastSavedCharacterFile !== this.currentCharacterFile) {
                this.lastSavedCharacterGroup = this.currentCharacterGroup;
                this.lastSavedCharacterFile = this.currentCharacterFile;
                // Rebuild children map to update data-location attributes
                this.buildChildrenMap();
                this.shadowRoot.querySelector('app-overlay').setAttribute("overlay-title", `Working on: ${JSON.stringify(escapeHTML(this.currentCharacterName))}`);
            }
        });
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                @import "./components/character.css";
            </style>
            <app-overlay overlay-title="Working on: ${JSON.stringify(escapeHTML(this.currentCharacterName))}" confirm-text="Apply Changes" cancel-text="Go Back" special-button-text="Help">
            </app-overlay>
        `;
    }
}

customElements.define('app-character', CharacterOverlay);