// frontend/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    const initButton = document.getElementById('initVmButton');
    const stepButton = document.getElementById('stepVmButton');
    const autoStepButton = document.getElementById('autoStepButton');
    const stopAutoStepButton = document.getElementById('stopAutoStepButton');
    
    let stepCounter = 0;
    let autoStepIntervalId = null;
    const autoStepDelay = 300; 
    let currentVmState = null;

    async function autoProvideInputAndContinue() {
        if (!currentVmState || !currentVmState.needs_input) {
            console.log("AutoProvideInput: Condition not met or not needed.");
            return;
        }
        
        console.log("AutoProvideInput: VM needs input, automatically calling /api/provide_input. Phase:", currentVmState.interaction_phase);
        const result = await provideVmInput(); 
        
        if (result && result.success) {
            console.log('AutoProvideInput: Input auto-provided, New State:', result.state);
            processVmState(result.state); 
        } else {
            console.error('AutoProvideInput: Failed:', result);
            const errorMsg = result ? (result.error || "Auto Provide Input API call failed.") : "Auto Provide Input API call failed.";
            processVmState({
                ...(currentVmState || {}),
                halted: true, error: errorMsg, needs_input: false
            });
            if (autoStepIntervalId) stopAutoStepping();
        }
    }

    function processVmState(state) {
        currentVmState = state;
        updateVmStateDisplay(state, stepCounter);

        if (state.halted || state.error) {
            stepButton.disabled = true;
            autoStepButton.disabled = true; 
            if (autoStepIntervalId) stopAutoStepping();
        } else {
            const canManuallyStep = !state.needs_input;
            stepButton.disabled = !canManuallyStep;
            autoStepButton.disabled = !canManuallyStep;

            if (state.needs_input) {
                if (autoStepIntervalId) {
                    console.log("ProcessVmState: Needs input, auto-stepper will handle providing it.");
                } else {
                    console.log("ProcessVmState: Needs input during manual step, auto-providing.");
                    autoProvideInputAndContinue(); 
                }
            }
        }
    }

    function resetDemoState() {
        stepCounter = 0;
        if (typeof resetUiHighlights === 'function') {
            resetUiHighlights();
        }
        const initialDisplayState = { 
            instruction_pointer: -1, // Use -1 for IP before init
            stack: [], 
            output_log: [], 
            halted: false, 
            error: null, 
            program_memory: [], 
            needs_input: false, 
            current_target: null, 
            interaction_phase: "IDLE",
            difficulty_level: "N/A" 
        };
        processVmState(initialDisplayState); // Call processVmState to set initial UI
        
        initButton.disabled = false;
        stepButton.disabled = true;
        autoStepButton.disabled = true;
        stopAutoStepButton.disabled = true;
    }

    resetDemoState();

    initButton.addEventListener('click', async () => {
        console.log('Initializing VM...');
        if (autoStepIntervalId) stopAutoStepping();
        resetDemoState(); 
        
        const result = await initVm();
        if (result && result.success) {
            console.log('VM Initialized:', result.state);
            processVmState(result.state);
        } else {
            console.error('VM Initialization failed:', result);
            const errorMsg = result ? (result.error || "Initialization API call failed.") : "Initialization API call failed.";
            processVmState({
                instruction_pointer: -1, stack: [], output_log: [], halted: false, 
                error: errorMsg, program_memory: [], needs_input: false,
                current_target: null, interaction_phase: "IDLE", difficulty_level: "N/A"
            });
        }
    });

    stepButton.addEventListener('click', async () => {
        if (!currentVmState || currentVmState.halted || currentVmState.error || currentVmState.needs_input) {
            console.log("Cannot step manually: VM not ready or needs input (which should be auto-handled).");
            return;
        }

        stepCounter++;
        console.log(`Stepping VM... (Manual Step ${stepCounter})`);
        const result = await stepVm(); 
        if (result && result.success) {
            processVmState(result.state);
        } else {
            console.error('VM Step failed:', result);
            const errorMsg = result ? (result.error || "Step API call failed.") : "Step API call failed.";
            processVmState({ ...(currentVmState || {}), halted: true, error: errorMsg, needs_input: false });
        }
    });

    function performAutoStep() {
        if (!currentVmState || currentVmState.halted || currentVmState.error) {
            stopAutoStepping();
            return;
        }

        if (currentVmState.needs_input) {
            console.log("Auto-step: VM needs input, auto-providing.");
            autoProvideInputAndContinue(); 
        } else {
            stepCounter++;
            console.log(`Auto-Stepping VM... (Step ${stepCounter})`);
            stepVm().then(result => {
                if (autoStepIntervalId === null) return; 
                if (result && result.success) {
                    processVmState(result.state);
                } else {
                    console.error('VM Auto-Step failed:', result);
                    const errorMsg = result ? (result.error || "Auto-Step API call failed.") : "Auto-Step API call failed.";
                    processVmState({ ...(currentVmState || {}), halted: true, error: errorMsg, needs_input: false });
                    stopAutoStepping();
                }
            }).catch(error => {
                if (autoStepIntervalId === null) return;
                console.error('Network or other error during auto-step:', error);
                processVmState({ ...(currentVmState || {}), halted: true, error: "Network error during auto-step.", needs_input: false });
                stopAutoStepping();
            });
        }
    }

    function startAutoStepping() {
        if (autoStepIntervalId) return;
        if (!currentVmState || currentVmState.halted || currentVmState.error) {
            console.log("Cannot start auto-step: VM not ready, halted, or errored.");
            return;
        }
        console.log("Starting auto-step...");
        autoStepButton.disabled = true;
        stopAutoStepButton.disabled = false;
        stepButton.disabled = true; 
        
        performAutoStep(); 
        autoStepIntervalId = setInterval(performAutoStep, autoStepDelay);
    }

    function stopAutoStepping() {
        if (autoStepIntervalId) {
            clearInterval(autoStepIntervalId);
            autoStepIntervalId = null;
            console.log("Auto-step stopped.");
        }
        const isVmRunnable = currentVmState && !currentVmState.halted && !currentVmState.error && !currentVmState.needs_input;
        autoStepButton.disabled = !isVmRunnable;
        stopAutoStepButton.disabled = true;
        stepButton.disabled = !isVmRunnable;
    }

    autoStepButton.addEventListener('click', startAutoStepping);
    stopAutoStepButton.addEventListener('click', stopAutoStepping);
});