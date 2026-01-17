/**
 * Form Visibility System
 * Declarative data-attribute driven form field visibility and state management.
 *
 * Data attributes:
 *   data-fv-show="field_id=value"    Show element when field equals value
 *   data-fv-show="field_id"          Show element when checkbox is checked
 *   data-fv-hide="field_id=value"    Hide element when condition met
 *   data-fv-disable="field_id=value" Disable element when condition met
 *   data-fv-require="field_id"       Additional AND condition (must also be true)
 *   data-fv-excludes="field_id"      Mutual exclusion for checkboxes
 *
 * Events:
 *   fv:visibility-changed - Fired on elements when visibility changes
 *   fv:state-changed      - Fired on elements when enabled/disabled changes
 */
(function() {
    'use strict';

    const FV_SHOW = 'data-fv-show';
    const FV_HIDE = 'data-fv-hide';
    const FV_DISABLE = 'data-fv-disable';
    const FV_REQUIRE = 'data-fv-require';
    const FV_EXCLUDES = 'data-fv-excludes';

    // Track all controlled elements and their source fields
    let controllers = new Map();
    let controlledElements = [];

    function parseCondition(condition) {
        if (!condition) return null;
        const parts = condition.split('=');
        return {
            fieldId: parts[0].trim(),
            value: parts.length > 1 ? parts[1].trim() : null
        };
    }

    function getFieldValue(fieldId) {
        const el = document.getElementById(fieldId);
        if (!el) return null;

        if (el.type === 'checkbox') {
            return el.checked;
        }
        if (el.type === 'radio') {
            const checked = document.querySelector(`input[name="${el.name}"]:checked`);
            return checked ? checked.value : null;
        }
        if (el.tagName === 'SELECT' && el.multiple) {
            return Array.from(el.selectedOptions).map(o => o.value);
        }
        return el.value;
    }

    function checkCondition(condition) {
        if (!condition) return true;
        const parsed = parseCondition(condition);
        if (!parsed) return true;

        const value = getFieldValue(parsed.fieldId);

        // Boolean check for checkboxes (no value specified)
        if (parsed.value === null) {
            return Boolean(value);
        }

        // Value comparison
        if (Array.isArray(value)) {
            return value.includes(parsed.value);
        }
        return String(value) === parsed.value;
    }

    function setElementVisibility(el, visible) {
        const wasHidden = el.style.display === 'none';
        el.style.display = visible ? '' : 'none';

        if (wasHidden !== !visible) {
            el.dispatchEvent(new CustomEvent('fv:visibility-changed', {
                bubbles: true,
                detail: { visible }
            }));
        }
    }

    function setElementDisabled(el, disabled) {
        const wrapper = el.closest('[data-disable-wrapper]') || el;
        const inputs = el.querySelectorAll('input, select, textarea');
        const wasDisabled = wrapper.classList.contains('opacity-50');

        // Handle multi-select options
        inputs.forEach(input => {
            if (input.tagName === 'SELECT' && input.multiple) {
                Array.from(input.options).forEach(opt => opt.disabled = disabled);
            }
            input.disabled = disabled;
        });

        // Also handle the wrapper element itself if it's an input
        if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) {
            if (el.tagName === 'SELECT' && el.multiple) {
                Array.from(el.options).forEach(opt => opt.disabled = disabled);
            }
            el.disabled = disabled;
        }

        wrapper.classList.toggle('opacity-50', disabled);
        wrapper.classList.toggle('pointer-events-none', disabled);

        if (wasDisabled !== disabled) {
            el.dispatchEvent(new CustomEvent('fv:state-changed', {
                bubbles: true,
                detail: { disabled }
            }));
        }
    }

    function handleMutualExclusion(sourceEl) {
        const excludes = sourceEl.getAttribute(FV_EXCLUDES);
        if (!excludes || sourceEl.type !== 'checkbox' || !sourceEl.checked) return;

        const targetEl = document.getElementById(excludes);
        if (targetEl && targetEl.type === 'checkbox' && targetEl.checked) {
            targetEl.checked = false;
            targetEl.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function updateElement(el) {
        const showCondition = el.getAttribute(FV_SHOW);
        const hideCondition = el.getAttribute(FV_HIDE);
        const disableCondition = el.getAttribute(FV_DISABLE);
        const requireCondition = el.getAttribute(FV_REQUIRE);

        // Check require condition (AND logic)
        const requireMet = checkCondition(requireCondition);

        // Show/hide logic
        let visible = true;
        if (showCondition) {
            visible = checkCondition(showCondition) && requireMet;
        }
        if (hideCondition && checkCondition(hideCondition)) {
            visible = false;
        }

        setElementVisibility(el, visible);

        // Disable logic
        if (disableCondition) {
            const shouldDisable = checkCondition(disableCondition);
            setElementDisabled(el, shouldDisable);
        }

        // When hidden, also disable all inputs inside
        if (!visible) {
            setElementDisabled(el, true);
        }
    }

    function updateAll() {
        controlledElements.forEach(updateElement);
    }

    function discoverControllers() {
        controllers.clear();
        controlledElements = [];

        const selector = `[${FV_SHOW}], [${FV_HIDE}], [${FV_DISABLE}], [${FV_REQUIRE}]`;
        document.querySelectorAll(selector).forEach(el => {
            controlledElements.push(el);

            // Extract field IDs from all conditions
            [FV_SHOW, FV_HIDE, FV_DISABLE, FV_REQUIRE].forEach(attr => {
                const condition = el.getAttribute(attr);
                if (condition) {
                    const parsed = parseCondition(condition);
                    if (parsed && parsed.fieldId) {
                        if (!controllers.has(parsed.fieldId)) {
                            controllers.set(parsed.fieldId, []);
                        }
                        if (!controllers.get(parsed.fieldId).includes(el)) {
                            controllers.get(parsed.fieldId).push(el);
                        }
                    }
                }
            });
        });

        // Also discover mutual exclusion relationships
        document.querySelectorAll(`[${FV_EXCLUDES}]`).forEach(el => {
            const excludes = el.getAttribute(FV_EXCLUDES);
            if (excludes && el.id) {
                // Track both directions
                [el.id, excludes].forEach(fieldId => {
                    if (!controllers.has(fieldId)) {
                        controllers.set(fieldId, []);
                    }
                });
            }
        });
    }

    function attachListeners() {
        controllers.forEach((elements, fieldId) => {
            const field = document.getElementById(fieldId);
            if (!field) return;

            const eventType = field.type === 'checkbox' || field.type === 'radio' ||
                             field.tagName === 'SELECT' ? 'change' : 'input';

            field.addEventListener(eventType, (e) => {
                handleMutualExclusion(e.target);
                updateAll();
            });
        });
    }

    function init() {
        discoverControllers();
        attachListeners();
        updateAll();
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose API for manual re-initialization
    window.FormVisibility = {
        init,
        update: updateAll,
        discover: discoverControllers
    };
})();
