import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from phase1_vm_enhancements import (
    chunk_push, chunk_add, chunk_print, chunk_poke_chunk,
    chunk_jump, chunk_build_chunk, chunk_dup, chunk_swap, chunk_drop,
    chunk_mod, chunk_input, chunk_compare_eq, chunk_jump_if_zero,
    chunk_random, OP_RANDOM,
    chunk_nop,
    OP_PUSH, _PRIME_IDX, get_prime, _extend_primes_to,
    PRIME_IDX_TRUE, PRIME_IDX_FALSE,
    OP_ADD,
    OP_NOP
)

FEEDBACK_SUCCESS_IDX = PRIME_IDX_TRUE
FEEDBACK_FAILURE_IDX = PRIME_IDX_FALSE
ATTEMPT_MODULUS_IDX = 10
ATTEMPT_INCREMENT_IDX = 1
RANDOM_MAX_EXCLUSIVE_IDX_FOR_OFFSET = 3 
MAX_FAILURES_BEFORE_STUCK_IDX = 3 
STUCK_SIGNAL_PRINT_VALUE_IDX = 99

# --- NEW CONSTANTS FOR DYNAMIC INSTRUCTION REPLACEMENT ---
MODIFICATION_SLOT_0_ADDR_IDX = 1 # We'll reserve ADDR 0 for the main PUSH, and use new slots
MODIFICATION_SLOT_1_ADDR_IDX = 2

UOR_DECISION_BUILD_PUSH_IDX = 0 # Internal representation for deciding to build a PUSH
UOR_DECISION_BUILD_ADD_IDX = 1  # Internal representation for deciding to build an ADD
UOR_DECISION_BUILD_NOP_IDX = 2  # Internal representation for deciding to build a NOP

# The UOR program will need to map UOR_DECISION_BUILD_PUSH_IDX to _PRIME_IDX[OP_PUSH] when building.
# And it will need operand for PUSH. For ADD/NOP, no operand needed *in the chunk itself*.
# --- END NEW CONSTANTS ---

def generate_goal_seeker_program():
    _extend_primes_to(max(35, STUCK_SIGNAL_PRINT_VALUE_IDX, MAX_FAILURES_BEFORE_STUCK_IDX, RANDOM_MAX_EXCLUSIVE_IDX_FOR_OFFSET, ATTEMPT_MODULUS_IDX, MODIFICATION_SLOT_0_ADDR_IDX, MODIFICATION_SLOT_1_ADDR_IDX, UOR_DECISION_BUILD_NOP_IDX) + 10) # Added new constants and a bit more buffer

    program_uor = []
    labels = {}

    # ADDR 0: PUSH current_value_to_work_with (This instruction is self-modified by POKE_CHUNK, based on success/failure of PRINTING the target)
    program_uor.append(chunk_push(FEEDBACK_FAILURE_IDX)) # Initial dummy value, will be overwritten by app.py
    labels["MAIN_EXECUTION_LOOP_START"] = 0
    # Stack: [current_val, last_pokéd_val_for_addr0, sfc, last_slot, last_instr_type]

    # ADDR 1: MODIFICATION_SLOT_0 - Initially a NOP
    program_uor.append(chunk_nop())
    # This is MODIFICATION_SLOT_0_ADDR_IDX if it's 1.
    if MODIFICATION_SLOT_0_ADDR_IDX != len(program_uor)-1:
        raise Exception(f"MODIFICATION_SLOT_0_ADDR_IDX mismatch: {MODIFICATION_SLOT_0_ADDR_IDX} vs {len(program_uor)-1}")
    labels["MODIFICATION_SLOT_0"] = MODIFICATION_SLOT_0_ADDR_IDX
    # Stack: depends on what's in SLOT_0. If NOP: [current_val, last_pokéd_val_for_addr0, sfc, last_slot, last_instr_type]

    # ADDR 2: MODIFICATION_SLOT_1 - Initially a NOP
    program_uor.append(chunk_nop())
    if MODIFICATION_SLOT_1_ADDR_IDX != len(program_uor)-1:
        raise Exception(f"MODIFICATION_SLOT_1_ADDR_IDX mismatch: {MODIFICATION_SLOT_1_ADDR_IDX} vs {len(program_uor)-1}")
    labels["MODIFICATION_SLOT_1"] = MODIFICATION_SLOT_1_ADDR_IDX
    # Stack: depends on what's in SLOT_1.

    # ADDR 3: DUP (the result of operations in slots, or current_val if slots were NOPs)
    program_uor.append(chunk_dup())
    # Stack: [val_after_slots, last_pokéd_val_for_addr0, sfc, last_slot, last_instr_type, val_after_slots_for_print]

    # ADDR 4: PRINT (the attempt)
    program_uor.append(chunk_print())
    # Stack: [val_after_slots, last_pokéd_val_for_addr0, sfc, last_slot, last_instr_type]

    # ADDR 5: INPUT (Get feedback from teacher: 0 for failure, 1 for success)
    program_uor.append(chunk_input())
    # Stack: [val_after_slots, last_pokéd_val_for_addr0, sfc, last_slot, last_instr_type, feedback_result]

    # ADDR 6: PUSH FEEDBACK_SUCCESS_IDX
    program_uor.append(chunk_push(FEEDBACK_SUCCESS_IDX))
    # Stack: [val_after_slots, last_pokéd_val_for_addr0, sfc, last_slot, last_instr_type, feedback_result, SUCCESS_IDX]

    # ADDR 7: COMPARE_EQ (feedback_result == SUCCESS_IDX ?)
    program_uor.append(chunk_compare_eq())
    # Stack: [val_after_slots, last_pokéd_val_for_addr0, sfc, last_slot, last_instr_type, comparison_bool_idx]

    # ADDR 8: PUSH address_of_HANDLE_FAILURE_ABSOLUTE (placeholder)
    program_uor.append(chunk_push(0))
    addr_idx_push_failure_target = len(program_uor) - 1

    # ADDR 9: SWAP
    program_uor.append(chunk_swap())

    # ADDR 10: JUMP_IF_ZERO (if comparison_bool_idx is 0 (false, i.e., failure), jump to HANDLE_FAILURE_ABSOLUTE)
    program_uor.append(chunk_jump_if_zero())
    # If SUCCESS (no jump):
    # Stack: [val_after_slots, last_pokéd_val_for_addr0, sfc, last_slot, last_instr_type]

    # ---- HANDLE SUCCESS ----
    labels["HANDLE_SUCCESS"] = len(program_uor)
    # Stack on entry: [succeeded_val, last_pokéd_val_for_addr0, sfc, last_slot_choice, last_instr_choice] (last_instr_choice is TOS)

    program_uor.append(chunk_drop()) # Drop last_instr_choice
    program_uor.append(chunk_drop()) # Drop last_slot_choice
    program_uor.append(chunk_drop()) # Drop sfc
    program_uor.append(chunk_drop()) # Drop last_pokéd_val_for_addr0 (this was for the PUSH(N) at addr 0 that just succeeded)
    program_uor.append(chunk_drop()) # Drop succeeded_val (the value that was printed and matched)
    # Stack is now empty: []

    program_uor.append(chunk_input()) # Get *new* target value from app.py for PUSH at ADDR 0
    # Stack: [new_target_for_addr0_push]
    program_uor.append(chunk_dup())
    # Stack: [new_target_for_addr0_poke (OI_A0), new_target_as_last_pokéd_for_addr0 (VCLP_A0)]
    program_uor.append(chunk_push(0)) # Reset session_failure_count to 0 (FC_A0)
    # Stack: [OI_A0, VCLP_A0, FC_A0] (FC_A0 is TOS)

    program_uor.append(chunk_push(0)) # Placeholder for BUILD_AND_POKE_ADDR_0_FROM_SUCCESS. This will be at index K.
    addr_idx_push_build_addr0_from_success = len(program_uor) - 1 # This will correctly be K.
    program_uor.append(chunk_jump()) # This will be at index K+1.
    # On JUMP, stack for BUILD_AND_POKE_ADDR_0_FROM_SUCCESS will be:
    # [OI_A0, VCLP_A0, FC_A0] (FC_A0 is TOS)

    # ---- HANDLE FAILURE ----
    labels["HANDLE_FAILURE_ABSOLUTE"] = len(program_uor)
    # Stack: [failed_attempt_val, last_pokéd_val_for_addr0, current_sfc, last_slot_choice, last_instr_choice]

    # Increment session_failure_count (SFC is at S-2, last_slot at S-1, last_instr at S-0)
    program_uor.append(chunk_swap()) # sfc, last_instr_choice, last_slot_choice
    program_uor.append(chunk_swap()) # last_instr_choice, sfc, last_slot_choice (no, this is wrong)
    # Stack: [FA, LPV_A0, SFC, LSC, LIC]
    # Goal: Increment SFC. Keep FA, LPV_A0. Decide new LSC, LIC. Calculate new PUSH value for Addr 0.
    #       Then POKE chosen slot, then POKE Addr 0.

    # Preserve FA, LPV_A0, LSC, LIC. Bring SFC to top.
    program_uor.append(chunk_swap()) # LIC, LSC
    program_uor.append(chunk_swap()) # LSC, SFC (LIC is now at bottom of these 3)
    program_uor.append(chunk_swap()) # SFC, LPV_A0 (LSC is bottom, LIC is S-1)
    # Stack: [FA, SFC, LPV_A0, LIC, LSC] -- this is getting complicated fast.

    program_uor.append(chunk_drop()) # last_instr_type
    program_uor.append(chunk_drop()) # last_slot
    # Stack: [failed_attempt_val, last_pokéd_val_for_addr0, current_sfc]

    # Stack on entry to this adapted block: [failed_attempt_val(FA), last_pokéd_val_for_addr0(LPV_A0), current_sfc(SFC)]
    program_uor.append(chunk_push(1)) # Increment SFC
    program_uor.append(chunk_add())
    # Stack: [FA, LPV_A0, new_sfc]

    # (Stuck signal logic - same as before)
    program_uor.append(chunk_dup()) # new_sfc for comparison
    program_uor.append(chunk_push(MAX_FAILURES_BEFORE_STUCK_IDX))
    program_uor.append(chunk_compare_eq())
    program_uor.append(chunk_push(0)) # placeholder for skip_stuck_print
    addr_idx_push_skip_stuck_print_target = len(program_uor) - 1
    program_uor.append(chunk_swap())
    program_uor.append(chunk_jump_if_zero()) # Jump if NOT stuck
    labels["PRINT_STUCK_SIGNAL_ABSOLUTE"] = len(program_uor)
    program_uor.append(chunk_push(STUCK_SIGNAL_PRINT_VALUE_IDX))
    program_uor.append(chunk_print())
    # Stack: [FA, LPV_A0, new_sfc_to_carry]

    labels["CALCULATE_NEXT_ADDR0_ATTEMPT_ABSOLUTE"] = len(program_uor)
    # Stack: [FA, LPV_A0, new_sfc_to_carry]
    program_uor.append(chunk_dup()) # FA for random calc
    program_uor.append(chunk_push(RANDOM_MAX_EXCLUSIVE_IDX_FOR_OFFSET))
    program_uor.append(chunk_random())
    program_uor.append(chunk_push(ATTEMPT_INCREMENT_IDX))
    program_uor.append(chunk_add()) # random_offset + 1
    program_uor.append(chunk_add()) # FA_copy + (random_offset+1)
    program_uor.append(chunk_push(ATTEMPT_MODULUS_IDX))
    program_uor.append(chunk_mod())
    # Stack: [FA, LPV_A0, new_sfc_to_carry, next_potential_addr0_attempt (NPA_A0)]

    # (Compare NPA_A0 with LPV_A0 - same 5-op sequence)
    program_uor.append(chunk_dup()) # NPA_A0
    program_uor.append(chunk_swap())
    program_uor.append(chunk_swap())
    program_uor.append(chunk_swap())
    program_uor.append(chunk_compare_eq()) # LPV_A0 == NPA_A0_copy?
    # Stack: [FA, new_sfc_to_carry, NPA_A0, comparison_result]

    program_uor.append(chunk_push(0)) # placeholder for process_different_addr0
    addr_idx_push_process_different_addr0_target = len(program_uor) - 1
    program_uor.append(chunk_swap())
    program_uor.append(chunk_jump_if_zero()) # Jump if DIFFERENT
    # Stack (if SAME): [FA, new_sfc_to_carry, NPA_A0_is_bad]

    labels["AVOID_RETRY_SAME_ADDR0_LOGIC_ABSOLUTE"] = len(program_uor)
    program_uor.append(chunk_push(1))
    program_uor.append(chunk_add())
    program_uor.append(chunk_push(ATTEMPT_MODULUS_IDX))
    program_uor.append(chunk_mod())
    # Stack: [FA, new_sfc_to_carry, new_distinct_addr0_attempt]

    program_uor.append(chunk_swap()) # new_sfc_to_carry, new_distinct_addr0_attempt
    program_uor.append(chunk_drop()) # drop FA
    # Stack: [new_distinct_addr0_attempt, new_sfc_to_carry]

    program_uor.append(chunk_push(0)) # placeholder for converge_addr0_poke_prep
    addr_idx_push_converge_addr0_from_avoid = len(program_uor) - 1
    program_uor.append(chunk_jump())
    # Stack (on jump): [new_distinct_addr0_attempt, new_sfc_to_carry]

    labels["PROCESS_DIFFERENT_ADDR0_ATTEMPT_ABSOLUTE"] = len(program_uor)
    # Stack from JUMP: [FA(garbage), new_sfc_to_carry, NPA_A0_is_good]
    program_uor.append(chunk_swap())
    program_uor.append(chunk_drop()) # drop FA
    # Stack: [NPA_A0_is_good_to_poke, new_sfc_to_carry]

    labels["CONVERGED_ADDR0_FAILURE_PATH_PREP_POKE"] = len(program_uor)
    # Stack: [final_addr0_attempt_to_poke, sfc_to_carry]

    program_uor.append(chunk_dup())
    # Stack: [OI_A0, FC, OI_A0_copy_as_VCLP_A0]
    program_uor.append(chunk_swap())
    # Stack: [OI_A0, VCLP_A0, FC] -- This is now [OperandIndex_for_PUSH_at_ADDR0, ValToCarryAsLastPokéd_for_ADDR0, FailCountToCarry]

    # ---- NOW, DECIDE WHICH SLOT TO MODIFY AND WITH WHAT INSTRUCTION ----
    # Stack: [OI_A0, VCLP_A0, FC]
    # We need to generate two random numbers:
    # 1. Slot choice: 0 for SLOT_0, 1 for SLOT_1 (random between 0 and 1 inclusive)
    # 2. Instruction type choice: 0 for PUSH, 1 for ADD, 2 for NOP (random 0-2 inclusive)

    # Choose slot (0 or 1)
    program_uor.append(chunk_push(2)) # Max exclusive for random (generates 0 or 1)
    program_uor.append(chunk_random())
    # Stack: [OI_A0, VCLP_A0, FC, slot_random_choice_0_or_1]
    program_uor.append(chunk_dup()) # Duplicate for carrying as last_slot_choice
    # Stack: [OI_A0, VCLP_A0, FC, slot_random_choice, slot_random_choice_to_carry_as_LSC]

    program_uor.append(chunk_drop()) # Drop slot_random_choice (we'll use slot_random_choice_to_carry_as_LSC and hardcode slot poke target)
    # Carry MODIFICATION_SLOT_0_ADDR_IDX as the "chosen slot" for this iteration.

    program_uor.append(chunk_push(MODIFICATION_SLOT_0_ADDR_IDX)) # This is LSC

    # Stack: [OI_A0, VCLP_A0, FC, slot_random_choice_to_carry_as_LSC(0/1), SLOT_0_ADDR_as_LSC_actual_val]
    program_uor.append(chunk_swap())
    program_uor.append(chunk_drop()) # Drop the 0/1 random choice, keep the actual addr as LSC
    # Stack: [OI_A0, VCLP_A0, FC, SLOT_0_ADDR_as_LSC] -- This LSC is the one to carry.

    program_uor.append(chunk_push(3)) # Max exclusive for random (0, 1, 2)
    program_uor.append(chunk_random())
    # Stack: [OI_A0, VCLP_A0, FC, LSC_slot0_addr, instr_type_decision_idx (LIC)]

    # then builds PUSH(OI_A0) and POKEs it to ADDR 0.
    program_uor.append(chunk_push(0)) # Placeholder for BUILD_SLOT_THEN_ADDR0_AND_POKE
    addr_idx_push_build_both_target_from_failure = len(program_uor) - 1
    program_uor.append(chunk_jump())
    # On JUMP, stack: [OI_A0, VCLP_A0, FC, LSC, LIC]

    # ---- BUILD_AND_POKE_ADDR_0_FROM_SUCCESS (From SUCCESS path, 3-item stack input) ----
    labels["BUILD_AND_POKE_ADDR_0_FROM_SUCCESS"] = len(program_uor)
    # Stack on entry: [OI_A0, VCLP_A0, FC_A0] (FC_A0 is TOS)

    # Current: [OI_A0(S2), VCLP_A0(S1), FC_A0(S0)]
    program_uor.append(chunk_swap())  # Stack: [OI_A0, FC_A0, VCLP_A0]
    program_uor.append(chunk_swap())  # Stack: [FC_A0, OI_A0, VCLP_A0]
    program_uor.append(chunk_swap())  # Stack: [FC_A0, VCLP_A0, OI_A0] (OI_A0 is TOS)

    # Build PUSH(OI_A0) chunk (standard logic)
    program_uor.append(chunk_dup())  # OI_A0 for build operand
    # Stack: [FC_A0, VCLP_A0, OI_A0_orig, OI_A0_copy_for_build]

    program_uor.append(chunk_push(5)) # exp_B
    program_uor.append(chunk_swap())  # Order for BUILD_CHUNK: exp_B, p_idx_B
    program_uor.append(chunk_push(4)) # exp_A
    program_uor.append(chunk_push(_PRIME_IDX[OP_PUSH])) # p_idx_A
    program_uor.append(chunk_push(2)) # num_factor_pairs
    # Stack for BUILD_CHUNK (top 5): [2_count, p_idx_A_OP_PUSH, 4_exp_A, OI_A0_copy_p_idx_B, 5_exp_B]

    # Underneath: [FC_A0, VCLP_A0, OI_A0_orig_to_preserve]
    program_uor.append(chunk_build_chunk())
    # Stack after BUILD_CHUNK: [FC_A0, VCLP_A0, OI_A0_orig_to_preserve, new_UOR_PUSH_chunk]

    program_uor.append(chunk_swap()) # Swaps OI_A0_orig and new_UOR_PUSH_chunk
    # Stack: [FC_A0, VCLP_A0, new_UOR_PUSH_chunk, OI_A0_orig_garbage]

    program_uor.append(chunk_drop()) # Drops OI_A0_orig_garbage
    # Stack: [FC_A0, VCLP_A0, new_UOR_PUSH_chunk] (new_UOR_PUSH_chunk is TOS)

    program_uor.append(chunk_push(labels["MAIN_EXECUTION_LOOP_START"])) # ADDR 0 for POKE target
    # Stack: [FC_A0, VCLP_A0, new_UOR_PUSH_chunk, 0_poke_addr]
    program_uor.append(chunk_poke_chunk()) # Pokes new_UOR_PUSH_chunk to ADDR 0
    # Stack after POKE: [FC_A0, VCLP_A0] (VCLP_A0 is TOS)

    program_uor.append(chunk_push(MODIFICATION_SLOT_0_ADDR_IDX)) # Default LSC_val (e.g., value 1)
    # Stack: [FC_A0, VCLP_A0, LSC_val]

    program_uor.append(chunk_push(UOR_DECISION_BUILD_NOP_IDX))   # Default LIC_val (e.g., value 2)
    # Stack: [FC_A0, VCLP_A0, LSC_val, LIC_val] (LIC_val is TOS)

    # SWAP S0,S1 (LIC,LSC)        -> [FC, VCLP, LIC, LSC]
    program_uor.append(chunk_swap())
    # SWAP S1,S2 (LSC,VCLP)       -> [FC, LSC, LIC, VCLP]
    program_uor.append(chunk_swap())
    # SWAP S2,S3 (LIC,FC)         -> [VCLP, LSC, FC, LIC] -- This is target order.
    program_uor.append(chunk_swap())
    # Stack is now: [VCLP_A0, LSC_val, FC_A0, LIC_val] -- My trace above was slightly off, let's verify carefully.

    # SWAP LSC,LIC -> [FC,VCLP,LIC,LSC]
    program_uor.append(chunk_swap())
    program_uor.append(chunk_swap())
    program_uor.append(chunk_swap())

    program_uor.append(chunk_swap())
    # SWAP  [FC,   LIC,  VCLP, LSC]
    program_uor.append(chunk_swap())
    # SWAP  [LIC,  FC,   VCLP, LSC]
    program_uor.append(chunk_swap())
    program_uor.append(chunk_swap())
    program_uor.append(chunk_swap())
    # SWAP VCLP,LIC -> [FC,LIC,VCLP,LSC]
    program_uor.append(chunk_swap())
    # SWAP FC,LIC -> [LIC,FC,VCLP,LSC] (LSC is TOS)
    program_uor.append(chunk_swap())
    # Stack is now: [LIC_val(S3), FC_A0(S2), VCLP_A0(S1), LSC_val(S0)]

    # Now to get VCLP_A0 to TOS:
    # SWAP LSC,VCLP -> [LIC,FC,LSC,VCLP]
    program_uor.append(chunk_swap())
    # Stack is: [LIC_val, FC_A0, LSC_val, VCLP_A0] (VCLP_A0 is TOS). This is correct.

    program_uor.append(chunk_push(labels["MAIN_EXECUTION_LOOP_START"]))
    program_uor.append(chunk_jump())

    # ---- BUILD_SLOT_THEN_ADDR0_AND_POKE (From FAILURE path - With Conditional Slot Build) ----
    labels["BUILD_SLOT_THEN_ADDR0_AND_POKE"] = len(program_uor)
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val_chosen, LIC_val_chosen] (LIC_val_chosen is TOS)

    program_uor.append(chunk_dup()) # Duplicate LIC_val for decision making
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val, LIC_val_orig, LIC_val_for_check]

    program_uor.append(chunk_push(UOR_DECISION_BUILD_ADD_IDX)) # Compare LIC_val_for_check with 1
    program_uor.append(chunk_compare_eq())
    program_uor.append(chunk_push(0)) # Placeholder for IF_LIC_IS_NOT_ADD
    addr_idx_push_if_lic_is_not_add = len(program_uor) - 1 # DEFINE PLACEHOLDER VAR
    program_uor.append(chunk_swap())
    program_uor.append(chunk_jump_if_zero()) # If NOT ADD, jump
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val, LIC_val_orig]
    program_uor.append(chunk_push(_PRIME_IDX[OP_ADD])) # slot_opcode_prime_idx = _PRIME_IDX[OP_ADD]
    program_uor.append(chunk_push(0)) # Placeholder for JUMP_TO_BUILD_SLOT_CHUNK_COMMON
    addr_idx_push_jump_to_build_common_from_add = len(program_uor) - 1 # DEFINE
    program_uor.append(chunk_jump())

    # --- Path if LIC IS NOT ADD ---
    labels["IF_LIC_IS_NOT_ADD"] = len(program_uor)
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val, LIC_val_orig] (LIC_val_orig is TOS)
    program_uor.append(chunk_dup()) # Duplicate LIC_val_orig for NOP check
    program_uor.append(chunk_push(UOR_DECISION_BUILD_NOP_IDX)) # Compare with 2
    program_uor.append(chunk_compare_eq())
    program_uor.append(chunk_push(0)) # Placeholder for IF_LIC_IS_NOT_NOP (meaning it's PUSH)
    addr_idx_push_if_lic_is_not_nop = len(program_uor) - 1 # DEFINE
    program_uor.append(chunk_swap())
    program_uor.append(chunk_jump_if_zero()) # If NOT NOP, jump

    # --- Path if LIC IS NOP (LIC_val_orig == UOR_DECISION_BUILD_NOP_IDX) ---
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val, LIC_val_orig_preserved]
    program_uor.append(chunk_push(_PRIME_IDX[OP_NOP])) # slot_opcode_prime_idx = _PRIME_IDX[OP_NOP]
    program_uor.append(chunk_push(0)) # Placeholder for JUMP_TO_BUILD_SLOT_CHUNK_COMMON
    addr_idx_push_jump_to_build_common_from_nop = len(program_uor) - 1 # DEFINE
    program_uor.append(chunk_jump())

    # --- Path if LIC IS PUSH (LIC_val_orig == UOR_DECISION_BUILD_PUSH_IDX (0)) ---
    labels["IF_LIC_IS_NOT_NOP"] = len(program_uor)
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val, LIC_val_orig_preserved]
    program_uor.append(chunk_push(_PRIME_IDX[OP_PUSH])) # slot_opcode_prime_idx = _PRIME_IDX[OP_PUSH]
    # Fall through to BUILD_SLOT_CHUNK_COMMON

    # --- BUILD_SLOT_CHUNK_COMMON ---
    labels["BUILD_SLOT_CHUNK_COMMON"] = len(program_uor)
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val, LIC_val_orig, slot_opcode_prime_idx] (slot_opcode_prime_idx is TOS)
    
    program_uor.append(chunk_dup()) # slot_opcode_prime_idx for check if PUSH
    program_uor.append(chunk_push(_PRIME_IDX[OP_PUSH]))
    program_uor.append(chunk_compare_eq()) # is slot_op_idx_for_check == _PRIME_IDX[OP_PUSH]?
    program_uor.append(chunk_push(0)) # Placeholder for JUMP_IF_SLOT_OP_NOT_PUSH
    addr_idx_jump_if_slot_op_not_push = len(program_uor) - 1 # DEFINE
    program_uor.append(chunk_swap())
    program_uor.append(chunk_jump_if_zero()) # If not PUSH, jump to build simple chunk

    program_uor.append(chunk_push(4))                  # PUSH exp_A (4 for OP_PUSH)
    program_uor.append(chunk_push(0))                  # PUSH p_idx_B (0 for operand prime_index 0)
    program_uor.append(chunk_push(5))                  # PUSH exp_B (5 for operand)
    program_uor.append(chunk_push(2))                  # PUSH count (2 pairs)
    # Stack before BUILD_CHUNK: [..., slot_op_idx_orig(p_idx_A), 4(exp_A), 0(p_idx_B), 5(exp_B), 2(count)] (count is TOS)

    program_uor.append(chunk_build_chunk())
    # Stack after build: [OI_A0, VCLP_A0, FC, LSC_val, LIC_val_orig, new_UOR_PUSH_fixed_val_chunk]

    program_uor.append(chunk_push(0)) # Placeholder for JUMP_AFTER_SLOT_CHUNK_BUILT
    addr_idx_jump_after_slot_chunk_built_for_push = len(program_uor) - 1 # DEFINE
    program_uor.append(chunk_jump())

    labels["JUMP_IF_SLOT_OP_NOT_PUSH_TARGET"] = len(program_uor)

    program_uor.append(chunk_push(4))       # PUSH exponent (4)
    # slot_op_idx_orig is already on stack (this will be p_idx_A)
    program_uor.append(chunk_push(1))       # PUSH count (1)
    # Stack: [..., LSC_val, LIC_val_orig, slot_op_idx_orig(p_idx_A), 4(exp_A), 1(count)] (count is TOS)

    program_uor.append(chunk_build_chunk()) # Builds ADD or NOP chunk
    # Stack after build: [OI_A0, VCLP_A0, FC, LSC_val, LIC_val_orig, new_UOR_ADD_or_NOP_chunk]

    labels["AFTER_SLOT_CHUNK_BUILT"] = len(program_uor)
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val(S-2), LIC_val_orig(S-1), new_slot_UOR_chunk(S0)]

    program_uor.append(chunk_swap()) # SWAP new_slot_UOR_chunk, LIC_val_orig
    # Stack: [OI_A0, VCLP_A0, FC, LSC_val, new_slot_UOR_chunk, LIC_val_orig]

    program_uor.append(chunk_swap()) # SWAP LIC_val_orig, LSC_val
    # Stack: [OI_A0, VCLP_A0, FC, LIC_val_orig, new_slot_UOR_chunk, LSC_val] (LSC_val is TOS)

    program_uor.append(chunk_poke_chunk()) # Pokes new_slot_UOR_chunk to LSC_val
    # Stack after POKE: [OI_A0, VCLP_A0, FC, LIC_val_orig] (LIC_val_orig is TOS)

    program_uor.append(chunk_swap())  # Stack: [OI_A0, VCLP_A0, LIC_val_orig, FC]
    program_uor.append(chunk_swap())  # Stack: [OI_A0, LIC_val_orig, VCLP_A0, FC]
    program_uor.append(chunk_swap())  # Stack: [LIC_val_orig, OI_A0, VCLP_A0, FC] (FC is TOS)

    # Build PUSH(OI_A0) chunk
    program_uor.append(chunk_dup()) # OI_A0 for build
    program_uor.append(chunk_push(5)) # exp_B
    program_uor.append(chunk_swap())  # order exp_B, p_idx_B
    program_uor.append(chunk_push(4)) # exp_A
    program_uor.append(chunk_push(_PRIME_IDX[OP_PUSH])) # p_idx_A
    program_uor.append(chunk_push(2)) # count
    program_uor.append(chunk_build_chunk())
    # Stack: [LIC_val_orig, FC, VCLP_A0, OI_A0_orig, new_UOR_PUSH_ADDR0_chunk]
    program_uor.append(chunk_swap())
    program_uor.append(chunk_drop())
    # Stack: [LIC_val_orig, FC, VCLP_A0, new_UOR_PUSH_ADDR0_chunk]
    program_uor.append(chunk_push(labels["MAIN_EXECUTION_LOOP_START"])) # ADDR 0
    program_uor.append(chunk_poke_chunk())
    # Stack: [LIC_val_orig, FC, VCLP_A0] (VCLP_A0 is TOS)

    program_uor.append(chunk_push(MODIFICATION_SLOT_0_ADDR_IDX)) # LSC_val_to_carry
    # Stack: [LIC_val_orig(S3), FC(S2), VCLP_A0(S1), LSC_val(S0)] (LSC_val is TOS)

    program_uor.append(chunk_swap()) # Swaps LSC_val(S0), VCLP_A0(S1) -> [LIC_orig, FC, LSC_val, VCLP_A0]
    program_uor.append(chunk_swap()) # Swaps LSC_val(S1), FC(S2)   -> [LIC_orig, LSC_val, FC, VCLP_A0]
    # Stack is now [LIC_val_orig, LSC_val, FC, VCLP_A0] (VCLP_A0 is TOS). This is the correct final order.
    
    program_uor.append(chunk_push(labels["MAIN_EXECUTION_LOOP_START"]))
    program_uor.append(chunk_jump())

    # --- ADD PATH --- (Executed if LIC == UOR_DECISION_BUILD_ADD_IDX)
    program_uor.append(chunk_drop()) # Drop LIC used for check
    program_uor.append(chunk_push(_PRIME_IDX[OP_ADD])) # Opcode prime index for ADD
    program_uor.append(chunk_push(0)) # Placeholder for JUMP_TO_BUILD_COMMON_SLOT_OP
    addr_idx_push_jump_to_build_common_from_add = len(program_uor) - 1
    program_uor.append(chunk_jump())

    # --- NOT ADD PATH --- (Jumped here if LIC != UOR_DECISION_BUILD_ADD_IDX)
    labels["IF_LIC_IS_ADD_JUMP_TARGET"] = len(program_uor) # This label name is confusing, it's where it jumps if NOT ADD
    program_uor.append(chunk_drop()) # Drop LIC used for check
    # Stack: [LIC_original, LSC, FC, VCLP_A0, OI_A0]

    program_uor.append(chunk_dup()) # LIC_original for next check
    program_uor.append(chunk_push(UOR_DECISION_BUILD_NOP_IDX)) # Check if NOP
    program_uor.append(chunk_compare_eq())
    program_uor.append(chunk_push(0)) # Placeholder for IF_LIC_IS_NOP
    addr_idx_push_if_lic_is_nop = len(program_uor) - 1
    program_uor.append(chunk_swap())
    program_uor.append(chunk_jump_if_zero()) # If LIC == NOP, no jump. If LIC != NOP, jump.

    # --- NOP PATH --- (Executed if LIC == UOR_DECISION_BUILD_NOP_IDX)
    program_uor.append(chunk_drop()) # Drop LIC used for check
    program_uor.append(chunk_push(_PRIME_IDX[OP_NOP])) # Opcode prime index for NOP
    program_uor.append(chunk_push(0)) # Placeholder for JUMP_TO_BUILD_COMMON_SLOT_OP
    addr_idx_push_jump_to_build_common_from_nop = len(program_uor) - 1
    program_uor.append(chunk_jump())

    # --- PUSH PATH --- (Default if not ADD and not NOP, assumes LIC was UOR_DECISION_BUILD_PUSH_IDX)
    labels["IF_LIC_IS_NOP_JUMP_TARGET"] = len(program_uor) # Jumped here if LIC != NOP (so it must be PUSH by exclusion)
    program_uor.append(chunk_drop()) # Drop LIC used for check
    program_uor.append(chunk_push(_PRIME_IDX[OP_PUSH])) # Opcode prime index for PUSH
    # This chosen_opcode_prime_idx is for the SLOT instruction.
    # Stack: [LIC_orig, LSC, FC, VCLP_A0, OI_A0, chosen_opcode_prime_idx_for_slot]

    labels["BUILD_COMMON_SLOT_OP"] = len(program_uor)
    program_uor.append(chunk_dup()) # slot_op_idx for build
    program_uor.append(chunk_push(4)) # exp_A for slot_op_idx
    # Stack: [LIC, LSC, FC, VCLP_A0, OI_A0, slot_op_idx_orig, slot_op_idx_copy, 4_exp_A]

    # Conditional operand for PUSH in slot
    program_uor.append(chunk_dup()) # slot_op_idx_copy for checking if it's PUSH
    program_uor.append(chunk_swap()) # put 4_exp_A under it
    program_uor.append(chunk_push(_PRIME_IDX[OP_PUSH]))
    program_uor.append(chunk_compare_eq()) # is slot_op_idx_copy == OP_PUSH?
    program_uor.append(chunk_push(0)) # placeholder for JUMP_IF_SLOT_OP_NOT_PUSH
    addr_idx_jump_if_slot_op_not_push = len(program_uor) - 1
    program_uor.append(chunk_swap())
    program_uor.append(chunk_jump_if_zero()) # If not PUSH, jump to skip operand build
    # Stack: [LIC, LSC, FC, VCLP_A0, OI_A0, slot_op_idx_orig, slot_op_idx_copy_was_push, 4_exp_A]

    program_uor.append(chunk_push(0)) # Operand for PUSH in slot (value 0)
    program_uor.append(chunk_push(5)) # exp_B
    program_uor.append(chunk_push(2)) # num_factor_pairs = 2 (Opcode, Operand)
    program_uor.append(chunk_build_chunk()) # Builds PUSH(0)
    # Stack: [LIC, LSC, FC, VCLP_A0, OI_A0, slot_op_idx_orig, new_slot_UOR_PUSH_0_chunk]

    program_uor.append(chunk_push(0)) # placeholder for JUMP_AFTER_SLOT_BUILD
    addr_idx_jump_after_slot_build_push = len(program_uor) - 1
    program_uor.append(chunk_jump())

    labels["JUMP_IF_SLOT_OP_NOT_PUSH_TARGET"] = len(program_uor)
    program_uor.append(chunk_push(1)) # num_factor_pairs = 1 (Opcode only)
    program_uor.append(chunk_build_chunk()) # Builds ADD or NOP
    # Stack: [LIC, LSC, FC, VCLP_A0, OI_A0, slot_op_idx_orig, new_slot_UOR_ADD_or_NOP_chunk]

    labels["AFTER_SLOT_CHUNK_BUILD"] = len(program_uor)
    # Stack: [LIC, LSC, FC, VCLP_A0, OI_A0, slot_op_idx_orig(garbage), new_slot_UOR_chunk]

    program_uor.append(chunk_swap())
    program_uor.append(chunk_drop()) # drop slot_op_idx_orig
    # Stack: [LIC, LSC, FC, VCLP_A0, OI_A0, new_slot_UOR_chunk]

    program_uor.append(chunk_swap()) # OI_A0, new_slot_UOR_chunk
    program_uor.append(chunk_swap()) # new_slot_UOR_chunk, VCLP_A0
    program_uor.append(chunk_swap()) # VCLP_A0, FC
    program_uor.append(chunk_swap()) # FC, LSC
    program_uor.append(chunk_swap()) # LSC, LIC
    # Stack: [new_slot_UOR_chunk, LSC, LIC, FC, VCLP_A0, OI_A0] -- LSC is S-1, new_slot_UOR is top

    program_uor.append(chunk_poke_chunk())
    # Stack: [LIC, FC, VCLP_A0, OI_A0] (LSC and new_slot_UOR consumed)

    # OI_A0 is on top.
    program_uor.append(chunk_dup()) # OI_A0 for build
    program_uor.append(chunk_push(5))
    program_uor.append(chunk_swap())
    program_uor.append(chunk_push(4))
    program_uor.append(chunk_push(_PRIME_IDX[OP_PUSH]))
    program_uor.append(chunk_push(2))
    program_uor.append(chunk_build_chunk())
    # Stack: [LIC, FC, VCLP_A0, OI_A0_orig, new_UOR_PUSH_ADDR0_chunk]

    program_uor.append(chunk_swap())
    program_uor.append(chunk_drop()) # drop OI_A0_orig
    # Stack: [LIC, FC, VCLP_A0, new_UOR_PUSH_ADDR0_chunk]

    program_uor.append(chunk_push(labels["MAIN_EXECUTION_LOOP_START"])) # ADDR 0 for POKE
    program_uor.append(chunk_poke_chunk())
    # Stack: [LIC, FC, VCLP_A0]

    program_uor.append(chunk_push(MODIFICATION_SLOT_0_ADDR_IDX)) # LSC
    # Stack: [LIC, FC, VCLP_A0, LSC]

    program_uor.append(chunk_swap()) # LSC, VCLP_A0
    program_uor.append(chunk_swap()) # VCLP_A0, FC
    program_uor.append(chunk_swap()) # FC, LIC
    # Stack: [VCLP_A0, FC, LSC, LIC] -- Correct order for carry

    program_uor.append(chunk_push(labels["MAIN_EXECUTION_LOOP_START"]))
    program_uor.append(chunk_jump())

    # --- Fill in JUMP targets (Reflects restored ambitious failure path) ---

    program_uor[addr_idx_push_failure_target] = chunk_push(labels["HANDLE_FAILURE_ABSOLUTE"])
    program_uor[addr_idx_push_build_addr0_from_success] = chunk_push(labels["BUILD_AND_POKE_ADDR_0_FROM_SUCCESS"])

    program_uor[addr_idx_push_skip_stuck_print_target] = chunk_push(labels["CALCULATE_NEXT_ADDR0_ATTEMPT_ABSOLUTE"])
    program_uor[addr_idx_push_process_different_addr0_target] = chunk_push(labels["PROCESS_DIFFERENT_ADDR0_ATTEMPT_ABSOLUTE"])
    program_uor[addr_idx_push_converge_addr0_from_avoid] = chunk_push(labels["CONVERGED_ADDR0_FAILURE_PATH_PREP_POKE"])
    
    program_uor[addr_idx_push_build_both_target_from_failure] = chunk_push(labels["BUILD_SLOT_THEN_ADDR0_AND_POKE"])

    # Jumps for LIC decision tree inside BUILD_SLOT_THEN_ADDR0_AND_POKE:
    program_uor[addr_idx_push_if_lic_is_not_add] = chunk_push(labels["IF_LIC_IS_NOT_ADD"])
    program_uor[addr_idx_push_jump_to_build_common_from_add] = chunk_push(labels["BUILD_SLOT_CHUNK_COMMON"])
    
    program_uor[addr_idx_push_if_lic_is_not_nop] = chunk_push(labels["IF_LIC_IS_NOT_NOP"])
    program_uor[addr_idx_push_jump_to_build_common_from_nop] = chunk_push(labels["BUILD_SLOT_CHUNK_COMMON"])

    # Jumps for slot PUSH operand decision inside BUILD_SLOT_CHUNK_COMMON:
    program_uor[addr_idx_jump_if_slot_op_not_push] = chunk_push(labels["JUMP_IF_SLOT_OP_NOT_PUSH_TARGET"])
    program_uor[addr_idx_jump_after_slot_chunk_built_for_push] = chunk_push(labels["AFTER_SLOT_CHUNK_BUILT"])

    # --- Length check (MUST BE UPDATED CAREFULLY) ---
    current_len = len(program_uor)
    print(f"Generated UOR program with {current_len} instructions.")
    print("Labels defined at (0-indexed):")
    for label, addr in sorted(labels.items(), key=lambda item: item[1]):
        print(f"  {label}: {addr}")

    print(f"DEBUG: Value of chunk_dup() is {chunk_dup()}")
    print(f"DEBUG: Value of chunk_push(2) is {chunk_push(2)}")
    if len(program_uor) > 83:
        print(f"DEBUG: program_uor[83] is {program_uor[83]}")
    else:
        print(f"DEBUG: program_uor length is only {len(program_uor)}")

    idx_for_push_target_in_success_path = 19
    idx_for_jump_in_success_path = 20

    print(f"--- Debugging Success Path Jump Target (addr_idx_push_build_addr0_from_success was {idx_for_push_target_in_success_path}) ---")
    if len(program_uor) > idx_for_push_target_in_success_path:
        print(f"DEBUG UOR GEN: program_uor[{idx_for_push_target_in_success_path}] (should be PUSH target_addr) = {program_uor[idx_for_push_target_in_success_path]}")
    else:
        print(f"DEBUG UOR GEN: program_uor index {idx_for_push_target_in_success_path} is out of bounds (len {len(program_uor)})")
    
    if len(program_uor) > idx_for_jump_in_success_path:
        print(f"DEBUG UOR GEN: program_uor[{idx_for_jump_in_success_path}] (should be JUMP) = {program_uor[idx_for_jump_in_success_path]}")
    else:
        print(f"DEBUG UOR GEN: program_uor index {idx_for_jump_in_success_path} is out of bounds (len {len(program_uor)})")
    
    print(f"DEBUG UOR GEN: chunk_jump() value should be = {chunk_jump()}")
    
    print(f"DEBUG UOR GEN: labels['BUILD_AND_POKE_ADDR_0_FROM_SUCCESS'] = {labels['BUILD_AND_POKE_ADDR_0_FROM_SUCCESS']}")
    target_addr_for_success_path = labels['BUILD_AND_POKE_ADDR_0_FROM_SUCCESS'] # Should be 77
    print(f"DEBUG UOR GEN: chunk_push({target_addr_for_success_path}) should be = {chunk_push(target_addr_for_success_path)}")
    print("--- End Debugging Success Path ---")

    return program_uor

if __name__ == '__main__':
    uor_chunks = generate_goal_seeker_program()
    
    output_dir = os.path.join(project_root, "backend", "uor_programs")
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, "goal_seeker_demo.uor.txt")

    with open(output_filename, "w") as f:
        for chunk_val in uor_chunks:
            f.write(str(chunk_val) + "\n")
    print(f"Generated UOR program ({len(uor_chunks)} instructions) at: {output_filename}")