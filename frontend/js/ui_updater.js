// frontend/js/ui_updater.js

// Element selectors
const vmStackEl = document.getElementById('vmStack');
const vmOutputLogEl = document.getElementById('vmOutputLog');
const currentInstructionLineEl = document.getElementById('currentInstructionLine');
const explanationTextEl = document.getElementById('explanationText');
const largeOutputDisplayEl = document.getElementById('largeOutputDisplay');
const vmStatusLineEl = document.getElementById('vmStatusLine');
const projectDescriptionEl = document.getElementById('projectDescription');

let lastKnownProgramState = [];
let lastDisplayedIp = -1;
let lastDisplayedInstructionContent = "";
let lastPokedAddress = -1;

const detailedProjectDescription = `
    What am I looking at: PrimeOS VM autonomously executes code that modifies its own instructions in a loop, adapting its behavior to achieve externally set numerical target provided by an adaptive "teacher" component.
`;

if (projectDescriptionEl) {
    projectDescriptionEl.innerHTML = detailedProjectDescription;
}

// --- Detailed Explanations for goal_seeker_demo.uor.txt ---
// IPs are mapped from your generator output.
const detailedUorExplanations = {
    // MAIN_EXECUTION_LOOP_START
    "0": "MAIN LOOP: Executing self-modified PUSH at ADDR 0 to load current attempt value.",
    "1": "MAIN LOOP: Executing instruction in MODIFICATION_SLOT_0 (ADDR 1). Potentially NOP, ADD, or PUSH(0).", // MODIFICATION_SLOT_0: 1
    "2": "MAIN LOOP: Executing instruction in MODIFICATION_SLOT_1 (ADDR 2 - currently always NOP).", // MODIFICATION_SLOT_1: 2
    "3": "MAIN LOOP: DUPlicating the result of PUSH(ADDR 0) and slot operations for printing.",
    "4": "MAIN LOOP: PRINTing the VM's current numerical attempt (guess).",
    "5": "MAIN LOOP: OP_INPUT - VM requests feedback from Teacher (0 for fail, 1 for success).",
    "6": "MAIN LOOP: PUSHing '1' (success index) for comparison with Teacher's feedback.",
    "7": "MAIN LOOP: COMPARE_EQ - Checking if Teacher's feedback was 'success'.",
    "8": "MAIN LOOP: PUSHing jump target address (21) for failure path.", // Jump to HANDLE_FAILURE_ABSOLUTE
    "9": "MAIN LOOP: SWAP to prepare for conditional jump.",
    "10": "MAIN LOOP: JUMP_IF_ZERO - If feedback was NOT success, jump to HANDLE_FAILURE_ABSOLUTE (ADDR 21).",

    // HANDLE_SUCCESS
    "11": "SUCCESS PATH: Feedback was SUCCESS! Dropping last instruction type choice from stack.", // HANDLE_SUCCESS: 11
    "12": "SUCCESS PATH: Dropping last slot choice from stack.",
    "13": "SUCCESS PATH: Dropping session failure count (SFC) from stack.",
    "14": "SUCCESS PATH: Dropping last POKEd value for ADDR 0 from stack.",
    "15": "SUCCESS PATH: Dropping the succeeded attempt value from stack.",
    "16": "SUCCESS PATH: OP_INPUT - VM requests *new target value* from Teacher.",
    "17": "SUCCESS PATH: DUPlicating new target (one for POKE operand, one for VCLP).",
    "18": "SUCCESS PATH: PUSHing '0' to reset session failure count (SFC) to 0.",
    "19": "SUCCESS PATH: PUSHing jump target (77) for BUILD_AND_POKE_ADDR_0_FROM_SUCCESS.",
    "20": "SUCCESS PATH: JUMPing to ADDR 77 to build and POKE the new PUSH(target) for ADDR 0.",

    // HANDLE_FAILURE_ABSOLUTE
    "21": "FAILURE PATH: Feedback was FAILURE. Entry point.", // HANDLE_FAILURE_ABSOLUTE: 21
    "22": "FAILURE PATH: (Stack manipulation, was SWAP) Dropping last instruction type carried.", // First instruction in HANDLE_FAILURE_ABSOLUTE block (after label)
    "23": "FAILURE PATH: (Stack manipulation, was SWAP) Dropping last slot choice carried.",
    "24": "FAILURE PATH: PUSH 1 (to increment SFC).",
    "25": "FAILURE PATH: ADD to increment session failure count (SFC).",
    "26": "FAILURE PATH: DUP SFC for 'stuck' check.",
    "27": "FAILURE PATH: PUSH MAX_FAILURES_BEFORE_STUCK_IDX (3).",
    "28": "FAILURE PATH: COMPARE_EQ - Checking if SFC reached max failures.",
    "29": "FAILURE PATH: PUSH jump target (38) to skip printing 'stuck' signal.", // To CALCULATE_NEXT_ADDR0_ATTEMPT_ABSOLUTE
    "30": "FAILURE PATH: SWAP for conditional jump.",
    "31": "FAILURE PATH: JUMP_IF_ZERO - If NOT stuck, jump to ADDR 38.",
    // PRINT_STUCK_SIGNAL_ABSOLUTE: 36. If jump at 31 not taken, IP would be 32, 33, 34, 35, then 36
    // This part of code is: PUSH STUCK_SIGNAL_PRINT_VALUE_IDX, PRINT.
    // So, actual printing is at 37.
    "36": "FAILURE PATH: STUCK! PUSHing value 99 to print.", // PRINT_STUCK_SIGNAL_ABSOLUTE: 36
    "37": "FAILURE PATH: STUCK! PRINTing stuck signal (99).", // After PUSH 99
    
    // CALCULATE_NEXT_ADDR0_ATTEMPT_ABSOLUTE
    "38": "FAILURE PATH: Calculating next attempt for PUSH@0. DUP failed attempt value.", // CALCULATE_NEXT_ADDR0_ATTEMPT_ABSOLUTE: 38
    "39": "FAILURE PATH: PUSH RANDOM_MAX_EXCLUSIVE_IDX_FOR_OFFSET (3).",
    "40": "FAILURE PATH: OP_RANDOM to get random offset (0-2).",
    "41": "FAILURE PATH: PUSH ATTEMPT_INCREMENT_IDX (1).",
    "42": "FAILURE PATH: ADD to get (random_offset + 1).",
    "43": "FAILURE PATH: ADD to get (failed_attempt + random_offset + 1).",
    "44": "FAILURE PATH: PUSH ATTEMPT_MODULUS_IDX (10).",
    "45": "FAILURE PATH: MOD to get new potential attempt for ADDR 0.",
    // Compare new potential attempt (NPA_A0) with last POKEd value (LPV_A0)
    "46": "FAILURE PATH: DUP NPA_A0 for comparison.",
    "47": "FAILURE PATH: SWAP (part of 5-op sequence to bring LPV_A0 up for compare).",
    "48": "FAILURE PATH: SWAP.",
    "49": "FAILURE PATH: SWAP.",
    "50": "FAILURE PATH: COMPARE_EQ - (LPV_A0 == NPA_A0_copy?).",
    "51": "FAILURE PATH: PUSH jump target (62) if NPA_A0 is DIFFERENT from LPV_A0.", // To PROCESS_DIFFERENT_ADDR0_ATTEMPT_ABSOLUTE
    "52": "FAILURE PATH: SWAP for conditional jump.",
    "53": "FAILURE PATH: JUMP_IF_ZERO - If DIFFERENT, jump to ADDR 62.",

    // AVOID_RETRY_SAME_ADDR0_LOGIC_ABSOLUTE
    "54": "FAILURE PATH: New attempt was SAME as last. PUSH 1 to increment.", // AVOID_RETRY_SAME_ADDR0_LOGIC_ABSOLUTE: 54
    "55": "FAILURE PATH: ADD to increment the bad attempt.",
    "56": "FAILURE PATH: PUSH ATTEMPT_MODULUS_IDX (10).",
    "57": "FAILURE PATH: MOD to ensure new distinct attempt is within bounds.",
    "58": "FAILURE PATH: SWAP to prepare stack for convergence.",
    "59": "FAILURE PATH: DROP original failed_attempt_val (FA).",
    "60": "FAILURE PATH: PUSH jump target (64) to converge poke prep.", // To CONVERGED_ADDR0_FAILURE_PATH_PREP_POKE
    "61": "FAILURE PATH: JUMP to ADDR 64.",

    // PROCESS_DIFFERENT_ADDR0_ATTEMPT_ABSOLUTE
    "62": "FAILURE PATH: New attempt was DIFFERENT. SWAP to bring it up.", // PROCESS_DIFFERENT_ADDR0_ATTEMPT_ABSOLUTE: 62
    "63": "FAILURE PATH: DROP original failed_attempt_val (FA).",

    // CONVERGED_ADDR0_FAILURE_PATH_PREP_POKE
    "64": "FAILURE PATH: Converged. Stack: [final_addr0_attempt(OI_A0), sfc_to_carry(FC)]. DUP OI_A0.", // CONVERGED_ADDR0_FAILURE_PATH_PREP_POKE: 64
    "65": "FAILURE PATH: SWAP to get [OI_A0, VCLP_A0, FC].",
    // Slot Modification Logic
    "66": "FAILURE PATH (Slot Mod): PUSH 2 (for random choice 0 or 1 for slot - though simplified to always use slot 0).",
    "67": "FAILURE PATH (Slot Mod): OP_RANDOM (value ignored as slot choice is hardcoded next).",
    "68": "FAILURE PATH (Slot Mod): DUP random value (ignored).",
    "69": "FAILURE PATH (Slot Mod): DROP random value (ignored).",
    "70": "FAILURE PATH (Slot Mod): PUSH MODIFICATION_SLOT_0_ADDR_IDX (1) as chosen slot address (LSC).",
    "71": "FAILURE PATH (Slot Mod): SWAP (stack management).",
    "72": "FAILURE PATH (Slot Mod): DROP (random value again). Stack is now [OI_A0, VCLP_A0, FC, LSC=1].",
    "73": "FAILURE PATH (Slot Mod): PUSH 3 (for random choice 0, 1, or 2 for instruction type).",
    "74": "FAILURE PATH (Slot Mod): OP_RANDOM to choose instruction type (LIC) for slot.",
    "75": "FAILURE PATH (Slot Mod): PUSH jump target (109) to BUILD_SLOT_THEN_ADDR0_AND_POKE.",
    "76": "FAILURE PATH (Slot Mod): JUMP to ADDR 109.",

    // BUILD_AND_POKE_ADDR_0_FROM_SUCCESS
    "77": "BUILD/POKE (Success): Entry. Stack: [OI_A0, VCLP_A0, FC_A0=0]. Reordering for POKE.", // BUILD_AND_POKE_ADDR_0_FROM_SUCCESS: 77
    // ... up to IP 87 for build logic
    "87": "BUILD/POKE (Success): BUILD_CHUNK for PUSH(new_target).",
    "88": "BUILD/POKE (Success): SWAP after build.",
    "89": "BUILD/POKE (Success): DROP original OI_A0 used in build.",
    "90": "BUILD/POKE (Success): PUSH ADDR 0 (MAIN_EXECUTION_LOOP_START) for POKE target.",
    "91": "BUILD/POKE (Success): POKE_CHUNK - SELF-MODIFYING ADDR 0 with new PUSH(target).",
    "92": "BUILD/POKE (Success): PUSH MODIFICATION_SLOT_0_ADDR_IDX (1) as default LSC.",
    "93": "BUILD/POKE (Success): PUSH UOR_DECISION_BUILD_NOP_IDX (2) as default LIC.",
    // ... stack reordering SWAPs from 94 to 100
    "100": "BUILD/POKE (Success): Final SWAP. Stack is [LIC, LSC, FC, VCLP] for jump.", // (Order for PUSH consumption)
    "101": "BUILD_AND_POKE_ADDR_0_FROM_SUCCESS_JUMP: PUSH 0 (MAIN_EXEC_LOOP_START) & JUMP back.", // Actually PUSH 0 then JUMP at 102. The JUMP is to IP 0.

    // BUILD_SLOT_THEN_ADDR0_AND_POKE
    "109": "BUILD/POKE (Failure): Entry. Stack: [OI_A0, VCLP_A0, FC, LSC, LIC]. DUP LIC for decision.", // BUILD_SLOT_THEN_ADDR0_AND_POKE: 109
    "110": "BUILD/POKE (Failure): PUSH UOR_DECISION_BUILD_ADD_IDX (1).",
    "111": "BUILD/POKE (Failure): COMPARE_EQ - Is LIC == ADD?",
    "112": "BUILD/POKE (Failure): PUSH jump target (118) if LIC is NOT ADD.", // To IF_LIC_IS_NOT_ADD
    "113": "BUILD/POKE (Failure): SWAP for conditional jump.",
    "114": "BUILD/POKE (Failure): JUMP_IF_ZERO - If NOT ADD, jump to ADDR 118.",
    // Path if LIC IS ADD
    "115": "BUILD/POKE (Failure): LIC is ADD. PUSH _PRIME_IDX[OP_ADD].",
    "116": "BUILD/POKE (Failure): PUSH jump target (128) to BUILD_SLOT_CHUNK_COMMON.",
    "117": "BUILD/POKE (Failure): JUMP to ADDR 128.",

    // IF_LIC_IS_NOT_ADD
    "118": "BUILD/POKE (Failure): LIC was NOT ADD. DUP LIC for NOP check.", // IF_LIC_IS_NOT_ADD: 118
    "119": "BUILD/POKE (Failure): PUSH UOR_DECISION_BUILD_NOP_IDX (2).",
    "120": "BUILD/POKE (Failure): COMPARE_EQ - Is LIC == NOP?",
    "121": "BUILD/POKE (Failure): PUSH jump target (127) if LIC is NOT NOP (i.e., PUSH).", // To IF_LIC_IS_NOT_NOP
    "122": "BUILD/POKE (Failure): SWAP for conditional jump.",
    "123": "BUILD/POKE (Failure): JUMP_IF_ZERO - If NOT NOP, jump to ADDR 127.",
    // Path if LIC IS NOP
    "124": "BUILD/POKE (Failure): LIC is NOP. PUSH _PRIME_IDX[OP_NOP].",
    "125": "BUILD/POKE (Failure): PUSH jump target (128) to BUILD_SLOT_CHUNK_COMMON.",
    "126": "BUILD/POKE (Failure): JUMP to ADDR 128.",

    // IF_LIC_IS_NOT_NOP (means it's PUSH)
    "127": "BUILD/POKE (Failure): LIC was NOT NOP (so it's PUSH). PUSH _PRIME_IDX[OP_PUSH].", // IF_LIC_IS_NOT_NOP: 127
    
    // BUILD_SLOT_CHUNK_COMMON
    "128": "BUILD/POKE (Failure): Common logic to build slot chunk. DUP slot_opcode_prime_idx.", // BUILD_SLOT_CHUNK_COMMON: 128
    "129": "BUILD/POKE (Failure): PUSH _PRIME_IDX[OP_PUSH] for comparison.",
    "130": "BUILD/POKE (Failure): COMPARE_EQ - Is slot opcode PUSH?",
    "131": "BUILD/POKE (Failure): PUSH jump target (138) if slot opcode is NOT PUSH.", // Jumps to JUMP_IF_SLOT_OP_NOT_PUSH_TARGET (mapped from your output, this should map to 198 but logic here jumps to 138 as per script)

    "132": "BUILD/POKE (Failure): SWAP for conditional jump.",
    "133": "BUILD/POKE (Failure): JUMP_IF_ZERO - If slot op is NOT PUSH, jump to ADDR 198.",
    // SLOT OP IS PUSH: Build PUSH(0) for the slot
    "134": "BUILD/POKE (Failure): Slot Op is PUSH. PUSH 4 (exp_A).",
    "135": "BUILD/POKE (Failure): PUSH 0 (p_idx_B for PUSH(0) operand).",
    "136": "BUILD/POKE (Failure): PUSH 5 (exp_B).",
    "137": "BUILD/POKE (Failure): PUSH 2 (num_factor_pairs).",
    "138": "BUILD/POKE (Failure): BUILD_CHUNK for PUSH(0) for the slot.",
    "139": "BUILD/POKE (Failure): PUSH jump target (144) to AFTER_SLOT_CHUNK_BUILT.", // Jumps to AFTER_SLOT_CHUNK_BUILT (144)
    "140": "BUILD/POKE (Failure): JUMP to ADDR 144.",

    "198": "BUILD/POKE (Failure): Slot Op is NOT PUSH (ADD/NOP). PUSH 4 (exponent).", // JUMP_IF_SLOT_OP_NOT_PUSH_TARGET: 198
    "199": "BUILD/POKE (Failure): PUSH 1 (count for simple chunk). BUILD_CHUNK next.",

    "144": "BUILD/POKE (Failure): Slot chunk (PUSH(0)) built. Preparing to POKE slot.", // AFTER_SLOT_CHUNK_BUILT: 144 (first instance)

    "147": "BUILD/POKE (Failure): POKE_CHUNK - SELF-MODIFYING MODIFICATION_SLOT_0 (ADDR 1) with PUSH(0).",

    "162": "BUILD/POKE (Failure): POKE_CHUNK - SELF-MODIFYING ADDR 0 with new calculated PUSH.", // After building PUSH for ADDR0
    "169": "BUILD/POKE (Failure): JUMPing back to MAIN_EXECUTION_LOOP_START (ADDR 0).", // Last JUMP in this block

    // AFTER_SLOT_CHUNK_BUILD (Path from ADD/NOP slot build, this label is at 200 from your output)
    "200": "BUILD/POKE (Failure): Slot chunk (ADD/NOP) built. Preparing to POKE slot.", // AFTER_SLOT_CHUNK_BUILD: 200 (second instance)
    // ... similar POKE logic for slot then ADDR 0
    "203": "BUILD/POKE (Failure): POKE_CHUNK - SELF-MODIFYING MODIFICATION_SLOT_0 (ADDR 1) with ADD/NOP.",
    "218": "BUILD/POKE (Failure): POKE_CHUNK - SELF-MODIFYING ADDR 0 with new calculated PUSH.",
    "224": "BUILD/POKE (Failure): JUMPing back to MAIN_EXECUTION_LOOP_START (ADDR 0)." // Last instruction
};

// Generic explanations (fallback or for specific states)
const genericExplanations = {
    "-1": "SYSTEM BOOTING... PrimeOS Initializing. Standby for UOR program load.",
    "WAITING_INPUT_TARGET": "AWAITING DIRECTIVE... Teacher assessing performance. New target incoming.",
    "WAITING_INPUT_FEEDBACK": "TRANSMITTING ATTEMPT... Awaiting success/failure protocol from Teacher.",
    "GENERAL_PROCESSING": "EXECUTING UOR SEQUENCE... Internal state evolving.",
    "HALTED_ERROR": "SYSTEM CRITICAL ERROR! Execution halted. Check logs.",
    "HALTED_SUCCESS": "UOR PROGRAM TERMINATED. Goal cycle complete or manual halt.",
};

function updateVmStateDisplay(state, stepNumber = -1) {
    if (!state) {
        if (vmStatusLineEl) vmStatusLineEl.innerHTML = "Status: Error - No state received from VM.";
        return;
    }

    const currentIp = state.instruction_pointer !== undefined ? state.instruction_pointer : -1;
    const currentStack = state.stack !== undefined ? state.stack : [];
    const currentOutputLog = state.output_log !== undefined ? state.output_log : [];
    const isHalted = state.halted !== undefined ? state.halted : false;
    const currentError = state.error || 'None';

    if (vmStatusLineEl) {
        const stackTop = currentStack.length > 0 ? JSON.stringify(currentStack[currentStack.length - 1]) : 'Empty';
        let errorHtml = currentError !== 'None' ? `<span class="error-text">${currentError}</span>` : 'None';
        vmStatusLineEl.innerHTML = `Status: IP: <strong>${currentIp !== -1 ? currentIp : 'N/A'}</strong> | Stack Top: ${stackTop} | Halted: ${isHalted} | Error: ${errorHtml}`;
    }

    if (vmStackEl) {
        vmStackEl.textContent = currentStack.length > 0 ? currentStack.join(', ') : 'Empty';
    }

    if (vmOutputLogEl) {
        vmOutputLogEl.textContent = currentOutputLog.length > 0 ? currentOutputLog.join(', ') : 'No Output';
    }
    
    if (largeOutputDisplayEl) {
        let lastNumericOutput = "--";
        for (let i = currentOutputLog.length - 1; i >= 0; i--) {
            const val = currentOutputLog[i];
            if (val !== null && val !== "" && !isNaN(Number(val))) {
                lastNumericOutput = val;
                break;
            }
        }
        largeOutputDisplayEl.textContent = lastNumericOutput;
    }

    let pokedThisStep = false;
    if (state.program_memory && lastKnownProgramState && state.program_memory.length === lastKnownProgramState.length) {
        for (let i = 0; i < state.program_memory.length; i++) {
            if (state.program_memory[i].raw_chunk !== lastKnownProgramState[i].raw_chunk) {
                lastPokedAddress = i;
                pokedThisStep = true;
                break; 
            }
        }
    }

    if (state.program_memory) {
        renderProgramMemory(state.program_memory, currentIp, pokedThisStep);
        lastKnownProgramState = JSON.parse(JSON.stringify(state.program_memory)); 
    } else if (currentIp === -1) { 
        renderProgramMemory([], -1, false);
    }

    updateExplanation(currentIp, state, stepNumber);
}

function renderProgramMemory(programMemory, currentIp, pokedThisStep) {
    if (!currentInstructionLineEl) return;

    let newInstructionText = "VM not initialized or IP out of bounds.";
    let rawHtmlInstruction = newInstructionText; 

    if (programMemory && programMemory.length > 0 && currentIp >= 0 && currentIp < programMemory.length) {
        const instr = programMemory[currentIp];
        newInstructionText = `IP: ${instr.address} | Raw: ${instr.raw_chunk} | Decoded: ${instr.decoded || 'N/A'}`;
        rawHtmlInstruction = `<strong>IP: ${instr.address}</strong> | Raw: ${instr.raw_chunk} | Decoded: ${instr.decoded || 'N/A'}`;
    } else if (currentIp === -1 && (!programMemory || !programMemory.length)) {
        newInstructionText = "VM not initialized.";
        rawHtmlInstruction = newInstructionText;
    }

    currentInstructionLineEl.classList.remove('modified-value');
    if (pokedThisStep && currentIp === lastPokedAddress) {
        currentInstructionLineEl.classList.add('modified-value');
    }

    const ipChanged = currentIp !== lastDisplayedIp;
    const contentChanged = newInstructionText !== lastDisplayedInstructionContent;

    if (ipChanged || contentChanged) {
        currentInstructionLineEl.classList.add('fade-out');
        setTimeout(() => {
            currentInstructionLineEl.innerHTML = rawHtmlInstruction;
            currentInstructionLineEl.classList.remove('fade-out');
            currentInstructionLineEl.classList.add('fade-in');
            lastDisplayedIp = currentIp;
            lastDisplayedInstructionContent = newInstructionText; 
            setTimeout(() => {
                currentInstructionLineEl.classList.remove('fade-in');
            }, 400); 
        }, 400); 
    } else {
        if (currentInstructionLineEl.innerHTML !== rawHtmlInstruction) { 
             currentInstructionLineEl.innerHTML = rawHtmlInstruction;
        }
    }
}

function resetUiHighlights() {
    lastDisplayedIp = -1;
    lastDisplayedInstructionContent = "";
    lastPokedAddress = -1;
    if (currentInstructionLineEl) {
        currentInstructionLineEl.textContent = "VM not initialized.";
        currentInstructionLineEl.classList.remove('fade-in', 'fade-out', 'modified-value');
    }
}

function updateErrorDisplay(errorMessage) { 
    if (vmStatusLineEl) {
        vmStatusLineEl.innerHTML = `Status: Error - <span class="error-text">${errorMessage}</span>`;
    } else {
        alert(errorMessage); 
    }
}

function updateExplanation(currentIp, state, stepNumber) {
    let message = "";
    const currentTarget = state.current_target !== undefined && state.current_target !== null ? state.current_target : '???';
    const difficulty = state.difficulty_level || 'UNKNOWN';
    const attempts = state.attempts_on_target || 0;
    
    const ipToExplain = currentIp; 

    if (ipToExplain === -1 && (!state.program_memory || !state.program_memory.length) && stepNumber <= 0) {
        message = genericExplanations["-1"];
    } else if (state.error) {
        message = `${genericExplanations["HALTED_ERROR"]} Details: ${state.error}`;
    } else if (state.halted) {
        message = genericExplanations["HALTED_SUCCESS"];
    } else if (state.needs_input) {
        if (state.interaction_phase === "SEND_TARGET") {
            message = genericExplanations["WAITING_INPUT_TARGET"];
        } else if (state.interaction_phase === "AWAITING_ATTEMPT_RESULT") {
            message = genericExplanations["WAITING_INPUT_FEEDBACK"];
        } else {
            message = "SYSTEM PAUSED: Awaiting external data signal...";
        }
        message += ` Target Sector: ${currentTarget}. Difficulty Matrix: ${difficulty}. Attempt(s): ${attempts}.`;
    } else {
        const specificExplanation = detailedUorExplanations[ipToExplain.toString()];
        if (specificExplanation) {
            message = specificExplanation; // Use the detailed explanation directly
            // Add context about self-modification if it just happened to this instruction
            if (lastPokedAddress === ipToExplain && detailedUorExplanations[ipToExplain.toString()] && !detailedUorExplanations[ipToExplain.toString()].toLowerCase().includes("self-modify")) {
                 // Avoid adding if the explanation already mentions modification
                message += " (Instruction at this IP was just modified!)";
            }
        } else {
            const lastOutput = state.output_log && state.output_log.length > 0 ? state.output_log[state.output_log.length -1] : 'SILENT';
            message = `IP ${ipToExplain} (Processing): Target: ${currentTarget}. Diff: ${difficulty}. Last Signal: ${lastOutput}.`;
            if (lastPokedAddress !== -1) { 
                 message += ` Last Poke @ ADDR ${lastPokedAddress}.`;
            }
        }
    }
    
    if (explanationTextEl) {
        explanationTextEl.textContent = message;
    }
}