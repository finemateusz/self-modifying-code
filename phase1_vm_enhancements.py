#!/usr/bin/env python3
"""
Pure UOR — execution + integrity + NTT spectral (lossless full-complex)
=====================================================================
This script implements:
- A dynamic prime cache
- Data and exec opcodes with per-chunk checksum (exp⁶)
- Block framing via prime⁷ headers
- Forward & inverse Number-Theoretic Transform (NTT) mod 13 as a spectral operator
- Automatic inversion ensuring lossless round-trip
"""
from __future__ import annotations
import sys
from math import isqrt
from typing import List, Dict, Tuple, Iterator
import random

# ──────────────────────────────────────────────────────────────────────
# Prime cache & tags
# ──────────────────────────────────────────────────────────────────────
_PRIMES: List[int] = [2]
_PRIME_IDX: Dict[int,int] = {2: 0}

def _is_prime(n: int) -> bool:
    if n < 2: return False
    r = isqrt(n)
    for p_val in _PRIMES:
        if p_val > r: break
        if n % p_val == 0: return False
    return True

def _extend_primes_to(idx: int) -> None:
    if idx < 0: raise ValueError("Prime index cannot be negative.")
    if not _PRIMES:
        _PRIMES.append(2)
        _PRIME_IDX[2] = 0
        
    cand = _PRIMES[-1] + 1 if _PRIMES else 2
    while len(_PRIMES) <= idx:
        if _is_prime(cand):
            _PRIMES.append(cand)
            _PRIME_IDX[cand] = len(_PRIMES) - 1
        cand += 1

def get_prime(idx: int) -> int:
    if idx < 0: raise ValueError("Prime index cannot be negative")
    _extend_primes_to(idx)
    return _PRIMES[idx]

# --- Opcode and Tag Definitions
_extend_primes_to(5) 
OP_PUSH                   = get_prime(0)
OP_ADD                    = get_prime(1)
OP_PRINT                  = get_prime(2)
BLOCK_TAG                 = get_prime(3)
NTT_TAG                   = get_prime(4)
T_MOD_NTT                 = get_prime(5)
NTT_ROOT = 2

_extend_primes_to(14)
OP_DUP                    = get_prime(6)
OP_SWAP                   = get_prime(7)
OP_DROP                   = get_prime(8)
OP_PEEK_CHUNK             = get_prime(9)
OP_POKE_CHUNK             = get_prime(10)
OP_FACTORIZE              = get_prime(11)
OP_BUILD_CHUNK            = get_prime(12)
OP_GET_PRIME              = get_prime(13)
OP_GET_PRIME_IDX          = get_prime(14)

_extend_primes_to(18)
OP_NOP                    = get_prime(15)
OP_COMPARE_EQ             = get_prime(16)
OP_JUMP                   = get_prime(17)
OP_JUMP_IF_ZERO           = get_prime(18)

# --- NEW --- HALT Opcode (at prime index 19) ---
_extend_primes_to(19) 
OP_HALT                   = get_prime(19)

# --- NEW OP_CALL and OP_RETURN ---
_extend_primes_to(21) # Ensure primes up to index 21 are loaded
OP_CALL                   = get_prime(20)
OP_RETURN                 = get_prime(21)
OP_MOD                    = get_prime(22)
OP_INPUT                  = get_prime(23)
OP_RANDOM                 = get_prime(24)

# --- END NEW HALT Opcode ---

PRIME_IDX_TRUE = _PRIME_IDX[get_prime(1)] 
PRIME_IDX_FALSE = _PRIME_IDX[get_prime(0)]
_extend_primes_to(max(PRIME_IDX_TRUE, PRIME_IDX_FALSE))


# ──────────────────────────────────────────────────────────────────────
# Checksum attachment (exp 6)
# ──────────────────────────────────────────────────────────────────────

def _attach_checksum(raw: int, fac: List[Tuple[int,int]]) -> int:
    xor = 0
    for p, e in fac:
        if p not in _PRIME_IDX:
            _extend_primes_to(len(_PRIMES) + 5) 
            curr_p = _PRIMES[-1] + 1
            while curr_p <= p:
                if _is_prime(curr_p):
                    if curr_p not in _PRIME_IDX:
                        _PRIMES.append(curr_p)
                        _PRIME_IDX[curr_p] = len(_PRIMES) -1
                if curr_p == p and p not in _PRIME_IDX: 
                    if not _is_prime(p): 
                        raise ValueError(f"Factor {p} used in checksum is not prime.")
                    _PRIMES.append(p) 
                    _PRIME_IDX[p] = len(_PRIMES) -1
                curr_p +=1
            if p not in _PRIME_IDX:
                 raise ValueError(f"Prime {p} from factors not found in _PRIME_IDX for checksum.")
        xor ^= _PRIME_IDX[p] * e
    chk_prime_idx = xor 
    chk = get_prime(chk_prime_idx)
    return raw * (chk ** 6)

# ──────────────────────────────────────────────────────────────────────
# Chunk constructors
# ──────────────────────────────────────────────────────────────────────

def chunk_data(pos_idx: int, cp_idx: int) -> int:
    max_idx = max(pos_idx, cp_idx)
    _extend_primes_to(max_idx)
    p1, p2 = get_prime(pos_idx), get_prime(cp_idx)
    if p1 == p2:
        raw, fac = p1**3, [(p1, 3)]
    else:
        raw, fac = p1*(p2**2), [(p1, 1), (p2, 2)]
    return _attach_checksum(raw, fac)

def chunk_push(v_idx: int) -> int:
    _extend_primes_to(v_idx)
    p_operand = get_prime(v_idx)
    return _attach_checksum(OP_PUSH**4 * p_operand**5, [(OP_PUSH,4),(p_operand,5)])

def chunk_add() -> int:
    return _attach_checksum(OP_ADD**4, [(OP_ADD,4)])

def chunk_print() -> int:
    return _attach_checksum(OP_PRINT**4, [(OP_PRINT,4)])

def chunk_block_start(n_val_idx: int) -> int:
    _extend_primes_to(n_val_idx)
    lp = get_prime(n_val_idx)
    return _attach_checksum(BLOCK_TAG**7 * lp**5, [(BLOCK_TAG,7),(lp,5)])

def chunk_ntt(n_val_idx: int) -> int:
    _extend_primes_to(n_val_idx)
    lp = get_prime(n_val_idx)
    return _attach_checksum(NTT_TAG**4 * lp**5, [(NTT_TAG,4),(lp,5)])

def chunk_dup() -> int:
    return _attach_checksum(OP_DUP**4, [(OP_DUP, 4)])

def chunk_swap() -> int:
    return _attach_checksum(OP_SWAP**4, [(OP_SWAP, 4)])

def chunk_drop() -> int:
    return _attach_checksum(OP_DROP**4, [(OP_DROP, 4)])

def chunk_peek_chunk() -> int:
    return _attach_checksum(OP_PEEK_CHUNK**4, [(OP_PEEK_CHUNK, 4)])

def chunk_poke_chunk() -> int:
    return _attach_checksum(OP_POKE_CHUNK**4, [(OP_POKE_CHUNK, 4)])

def chunk_factorize() -> int:
    return _attach_checksum(OP_FACTORIZE**4, [(OP_FACTORIZE, 4)])

def chunk_build_chunk() -> int:
    return _attach_checksum(OP_BUILD_CHUNK**4, [(OP_BUILD_CHUNK, 4)])

def chunk_get_prime() -> int:
    return _attach_checksum(OP_GET_PRIME**4, [(OP_GET_PRIME, 4)])

def chunk_get_prime_idx() -> int:
    return _attach_checksum(OP_GET_PRIME_IDX**4, [(OP_GET_PRIME_IDX, 4)])

def chunk_nop() -> int:
    return _attach_checksum(OP_NOP**4, [(OP_NOP, 4)])

def chunk_compare_eq() -> int:
    return _attach_checksum(OP_COMPARE_EQ**4, [(OP_COMPARE_EQ, 4)])

def chunk_jump() -> int:
    return _attach_checksum(OP_JUMP**4, [(OP_JUMP, 4)])

def chunk_jump_if_zero() -> int:
    return _attach_checksum(OP_JUMP_IF_ZERO**4, [(OP_JUMP_IF_ZERO, 4)])

def chunk_halt() -> int:
    return _attach_checksum(OP_HALT**4, [(OP_HALT, 4)])

def chunk_call() -> int:
    # OP_CALL doesn't take an immediate operand in its chunk definition;
    # it expects the target address to be on the stack.
    # So, its UOR chunk is simple, just encoding the opcode itself.
    return _attach_checksum(OP_CALL**4, [(OP_CALL, 4)])

def chunk_return() -> int:
    return _attach_checksum(OP_RETURN**4, [(OP_RETURN, 4)])

def chunk_mod() -> int:
    return _attach_checksum(OP_MOD**4, [(OP_MOD, 4)])

def chunk_input() -> int:
    return _attach_checksum(OP_INPUT**4, [(OP_INPUT, 4)])

def chunk_random() -> int:
    return _attach_checksum(OP_RANDOM**4, [(OP_RANDOM, 4)])

# ──────────────────────────────────────────────────────────────────────
# Prime factorisation
# ──────────────────────────────────────────────────────────────────────

def _factor(x: int) -> List[Tuple[int,int]]:
    if x <= 0: raise ValueError("Cannot factor non-positive integer")
    fac = []
    i = 0
    d = x
    while True:
        p = get_prime(i)
        if p*p > d:
            break
        if d % p == 0:
            cnt = 0
            while d % p == 0:
                d //= p
                cnt += 1
            fac.append((p, cnt))
        i += 1
        if d == 1: break

    if d > 1:
        if d not in _PRIME_IDX:
            if _is_prime(d):
                 if d not in _PRIME_IDX :
                    _PRIMES.append(d)
                    _PRIME_IDX[d] = len(_PRIMES) -1
            else:
                raise ValueError(f"Remaining factor {d} in _factor is not prime.")
        fac.append((d,1))
    return fac

# ──────────────────────────────────────────────────────────────────────
# NTT forward & inverse (Using T_MOD_NTT)
# ──────────────────────────────────────────────────────────────────────

def ntt_forward(vec: List[int]) -> List[int]:
    N = len(vec)
    out = [0]*N
    for k in range(N):
        s = 0
        for n_idx in range(N): s += vec[n_idx] * pow(NTT_ROOT, n_idx*k, T_MOD_NTT)
        out[k] = s % T_MOD_NTT
    return out

def ntt_inverse(vec: List[int]) -> List[int]:
    N = len(vec)
    invN = pow(N, -1, T_MOD_NTT)
    out = [0]*N
    for n_idx in range(N):
        s = 0
        for k_idx in range(N): s += vec[k_idx] * pow(NTT_ROOT, -n_idx*k_idx, T_MOD_NTT)
        out[n_idx] = (s * invN) % T_MOD_NTT
    return out

# ──────────────────────────────────────────────────────────────────────
# VM execution
# ──────────────────────────────────────────────────────────────────────

def vm_execute(chunks_arg: List[int], initial_stack: List[int] = None) -> Iterator[Dict]:
    chunks: List[int] = list(chunks_arg)
    stack: List[int] = [] if initial_stack is None else list(initial_stack)
    i = 0
    instruction_count = 0
    MAX_INSTRUCTIONS = 1000
    target_uor_addr_of_dup = -1 # Set to a non-existent address or remove

    while i < len(chunks):
        output_for_this_iteration = None
        error_for_this_iteration = None
        halt_for_this_iteration = False

        if instruction_count >= MAX_INSTRUCTIONS:
            yield {
                'ip': i, 'stack': list(stack), 'program': list(chunks),
                'output_this_step': None, 'halt_flag': True,
                'error_msg': f"Max instructions ({MAX_INSTRUCTIONS}) reached at UOR_addr {i}."
            }
            break
        instruction_count += 1
        
        current_instruction_pointer_for_processing = i
        
        try:
            if current_instruction_pointer_for_processing == 79: # Check specific IP
                print(f"DEBUG VM (UOR_ADDR 79 Entry): About to process. Stack: {list(stack)}", file=sys.stderr)
            ck = chunks[current_instruction_pointer_for_processing]
            if current_instruction_pointer_for_processing == 83:
                print(f"DEBUG VM (UOR_ADDR 83): Fetched chunk ck = {ck}", file=sys.stderr)
                if ck == 69570654823675009:
                    print(f"DEBUG VM (UOR_ADDR 83): ck matches expected chunk_dup(). Good.", file=sys.stderr)
                elif ck == 44375184050000:
                    print(f"DEBUG VM (UOR_ADDR 83): ck matches chunk_push(2). THIS IS UNEXPECTED FROM FILE!", file=sys.stderr)
                else:
                    print(f"DEBUG VM (UOR_ADDR 83): ck is an UNKNOWN value: {ck}", file=sys.stderr)

            i += 1 
            
            if ck == 0:
                raise ValueError(f"Attempted to execute raw zero chunk at UOR_addr {current_instruction_pointer_for_processing}.")

            raw_factors_of_current_chunk = []
            try:
                raw_factors_of_current_chunk = _factor(ck)
            except ValueError as e:
                # print(f"DEBUG VM: Error during _factor({ck}) for instruction at UOR_addr {current_instruction_pointer_for_processing}: {e}", file=sys.stderr)
                raise 
            if current_instruction_pointer_for_processing == 83:
                print(f"DEBUG VM (UOR_ADDR 83): Raw factors of ck ({ck}): {raw_factors_of_current_chunk}", file=sys.stderr)
                expected_raw_factors_dup = [(get_prime(_PRIME_IDX[OP_DUP]), 4), (get_prime(_PRIME_IDX[OP_DUP]*4 % len(_PRIMES) if len(_PRIMES) > _PRIME_IDX[OP_DUP]*4 else _PRIME_IDX[OP_DUP]*4 ), 6)]

            # --- Checksum peeling and verification logic ---
            checksum_prime_val = None
            logical_factors_of_current_chunk: List[Tuple[int,int]] = [] 
            temp_factors_for_xor_calc = []
            potential_checksum_prime = None
            potential_checksum_exponent = 0

            for p, e_val in raw_factors_of_current_chunk:
                if e_val >= 6 and potential_checksum_prime is None:
                    potential_checksum_prime = p
                    potential_checksum_exponent = e_val
                else:
                    temp_factors_for_xor_calc.append((p, e_val))
            
            if potential_checksum_prime is not None:
                xor_sum_verify = 0
                for p_vf, e_vf in temp_factors_for_xor_calc:
                    if p_vf not in _PRIME_IDX:
                        _extend_primes_to(len(_PRIMES) + 20) 
                        if p_vf not in _PRIME_IDX:
                            if not _is_prime(p_vf):
                                 raise ValueError(f"Factor {p_vf} used in checksum verify is not prime.")
                            _PRIMES.append(p_vf)
                            _PRIME_IDX[p_vf] = len(_PRIMES) -1
                    xor_sum_verify ^= _PRIME_IDX[p_vf] * e_vf
                
                expected_checksum_prime = get_prime(xor_sum_verify)
                if potential_checksum_prime == expected_checksum_prime:
                    checksum_prime_val = potential_checksum_prime
                    if potential_checksum_exponent > 6:
                        logical_factors_of_current_chunk.append((checksum_prime_val, potential_checksum_exponent - 6))
                    logical_factors_of_current_chunk.extend(temp_factors_for_xor_calc)
                else:
                    logical_factors_of_current_chunk.append((potential_checksum_prime, potential_checksum_exponent))
                    logical_factors_of_current_chunk.extend(temp_factors_for_xor_calc)
            else:
                logical_factors_of_current_chunk = raw_factors_of_current_chunk

                # DEBUG PRINT FOR CHECKSUM VALIDATION
            if checksum_prime_val is None and ck != 1 and current_instruction_pointer_for_processing == 0 : # Trigger if error is imminent at addr 0
                print(f"DEBUG VM CHECKSUM (UOR_addr {current_instruction_pointer_for_processing}, chunk {ck}):", file=sys.stderr)
                print(f"  Raw Factors: {raw_factors_of_current_chunk}", file=sys.stderr)
                print(f"  Potential Checksum Prime (from raw factors): {potential_checksum_prime}, Exp: {potential_checksum_exponent}", file=sys.stderr)
                print(f"  Temp Factors for XOR Calc: {temp_factors_for_xor_calc}", file=sys.stderr)
                # Re-calculate xor_sum_verify here for debug to ensure scope or value hasn't changed
                debug_xor_sum = 0
                for p_debug, e_debug in temp_factors_for_xor_calc:
                    debug_xor_sum ^= _PRIME_IDX.get(p_debug, -1) * e_debug # Use .get for safety in debug
                print(f"  Calculated XOR Sum (for expected_checksum_prime_idx): {debug_xor_sum}", file=sys.stderr)
                if debug_xor_sum >=0:
                     print(f"  Expected Checksum Prime (from XOR sum): {get_prime(debug_xor_sum) if debug_xor_sum < len(_PRIMES) else 'XOR_SUM_OUT_OF_BOUNDS_FOR_CURRENT_PRIMES'}", file=sys.stderr)
                else: # Should not happen if .get default is -1 and product is taken
                     print(f"  XOR sum was negative or prime was not found in _PRIME_IDX during debug calc.", file=sys.stderr)
                print(f"  Condition (potential_checksum_prime == expected_checksum_prime): {potential_checksum_prime == (get_prime(debug_xor_sum) if debug_xor_sum >=0 and debug_xor_sum < len(_PRIMES) else -999)}", file=sys.stderr)
                print(f"  checksum_prime_val (set if condition was true): {checksum_prime_val}", file=sys.stderr)
            
            if checksum_prime_val is None and ck != 1: # ck != 1 allows raw 1 as a NOP-like value
                raise ValueError(f'Checksum missing or malformed for chunk {ck} at UOR_addr {current_instruction_pointer_for_processing}')
            # --- End of checksum logic ---

            if current_instruction_pointer_for_processing == 83:
                print(f"DEBUG VM (UOR_ADDR 83): Logical factors after checksum peel: {logical_factors_of_current_chunk}", file=sys.stderr)
                # Expected logical factors for chunk_dup() is [(OP_DUP, 4)] which is [(17, 4)]
                print(f"DEBUG VM (UOR_ADDR 83): Expected logical for chunk_dup() = [({OP_DUP}, 4)]", file=sys.stderr)
            data = logical_factors_of_current_chunk
            
            # ADD THIS DEBUG BLOCK
            if current_instruction_pointer_for_processing == 17: # Our target instruction
                print(f"DEBUG VM: Processing MODIFIED instruction 17. Chunk value: {ck}", file=sys.stderr)
                print(f"DEBUG VM: MODIFIED instr 17 - Raw factors: {raw_factors_of_current_chunk}", file=sys.stderr)
                print(f"DEBUG VM: MODIFIED instr 17 - Logical factors (data): {data}", file=sys.stderr)
                # Check how OP_PUSH would interpret these logical factors:
                temp_val_p_for_push = None
                if operation_prime == OP_PUSH: # Ensure we only do this if it's identified as PUSH
                    for p_iter_debug, e_iter_debug in data:
                        if p_iter_debug == OP_PUSH and e_iter_debug == 4:
                            pass
                        elif e_iter_debug == 5:
                            temp_val_p_for_push = p_iter_debug
                    print(f"DEBUG VM: MODIFIED instr 17 - Potential val_p_for_push based on data: {temp_val_p_for_push}", file=sys.stderr)
                    if temp_val_p_for_push:
                        print(f"DEBUG VM: MODIFIED instr 17 - Corresponding prime index for val_p_for_push: {_PRIME_IDX.get(temp_val_p_for_push, 'NOT_IN_PRIME_IDX')}", file=sys.stderr)

            if any(p==BLOCK_TAG and e_val==7 for p,e_val in data):
                lp = next(p_val for p_val,e_val in data if p_val!=BLOCK_TAG and e_val==5)
                count_idx = _PRIME_IDX[lp]
                inner_chunk_list = chunks[i : i + count_idx]
                i += count_idx 

                for recursive_yield_dict in vm_execute(inner_chunk_list, list(stack)): 
                    yield recursive_yield_dict
                continue

            if any(p==NTT_TAG and e_val==4 for p,e_val in data):
                lp = next(p_val for p_val,e_val in data if p_val!=NTT_TAG and e_val==5)
                count_idx = _PRIME_IDX[lp]
                inner_chunk_list_ntt = chunks[i : i + count_idx]
                i += count_idx
                vec_for_ntt = []
                for c_ntt in inner_chunk_list_ntt:                    
                    ntt_fac = _factor(c_ntt)
                    ntt_data_fac = []
                    temp_ntt_fac_for_xor = []
                    pot_ntt_chk_p, pot_ntt_chk_e = None, 0
                    for p2,e2 in ntt_fac:
                        if e2>=6 and pot_ntt_chk_p is None: pot_ntt_chk_p, pot_ntt_chk_e = p2,e2
                        else: temp_ntt_fac_for_xor.append((p2,e2))
                    if pot_ntt_chk_p:
                        xor_v = 0
                        for p_vf,e_vf in temp_ntt_fac_for_xor: xor_v ^= _PRIME_IDX[p_vf]*e_vf
                        if pot_ntt_chk_p == get_prime(xor_v):
                            if pot_ntt_chk_e > 6: ntt_data_fac.append((pot_ntt_chk_p, pot_ntt_chk_e-6))
                            ntt_data_fac.extend(temp_ntt_fac_for_xor)
                        else:
                            ntt_data_fac.append((pot_ntt_chk_p, pot_ntt_chk_e))
                            ntt_data_fac.extend(temp_ntt_fac_for_xor)
                    else: ntt_data_fac = ntt_fac
                    found_exp = next((e2_val for _,e2_val in ntt_data_fac if e2_val > 0), 0)
                    vec_for_ntt.append(found_exp)

                _ = ntt_inverse(ntt_forward(vec_for_ntt)) 
                for recursive_yield_dict_ntt in vm_execute(inner_chunk_list_ntt, list(stack)):
                    yield recursive_yield_dict_ntt
                continue

            operation_prime = None
            if len(data) == 1:
                p_single, e_single = data[0]
                if p_single == OP_PUSH and e_single == (4 + 5): 
                    operation_prime = OP_PUSH
            if operation_prime is None: 
                op_prime_candidates = []
                for p_op_scan, e_op_scan in data: 
                    if e_op_scan == 4:
                        op_prime_candidates.append(p_op_scan)
                if len(op_prime_candidates) == 1:
                    operation_prime = op_prime_candidates[0]
                elif len(op_prime_candidates) > 1:
                    raise ValueError(f"Multiple distinct primes with exponent 4 in chunk data: {data} at UOR_addr {current_instruction_pointer_for_processing}")
            
            # TEMPORARY DEBUG for JUMP at ADDR 22
            if current_instruction_pointer_for_processing == 22: # current_instruction_pointer_for_processing is IP *before* increment
                print(f"DEBUG VM (EXEC): At UOR ADDR 22 (target for JUMP processing). Chunk={ck}", file=sys.stderr)
                print(f"DEBUG VM (EXEC): Logical factors for instr 22: {data}", file=sys.stderr)
                print(f"DEBUG VM (EXEC): Determined operation_prime for instr 22: {operation_prime}", file=sys.stderr)
                if operation_prime == OP_JUMP:
                    print(f"DEBUG VM (EXEC): Instr 22 IS OP_JUMP. Stack before JUMP logic: {list(stack)}", file=sys.stderr)
                else:
                    print(f"DEBUG VM (EXEC): Instr 22 IS NOT OP_JUMP. It is {operation_prime}", file=sys.stderr)

            if current_instruction_pointer_for_processing >= 79 and current_instruction_pointer_for_processing <= 83:
                print(f"DEBUG VM (UOR_ADDR {current_instruction_pointer_for_processing}): Determined operation_prime = {operation_prime}", file=sys.stderr)
                if operation_prime:
                     print(f"DEBUG VM (UOR_ADDR {current_instruction_pointer_for_processing}): Determined operation_prime_idx = {_PRIME_IDX.get(operation_prime, 'NOT_IN_CACHE')}", file=sys.stderr)
                if current_instruction_pointer_for_processing <= 82: # Should be SWAP
                    print(f"DEBUG VM (UOR_ADDR {current_instruction_pointer_for_processing}): Expected operation_prime for SWAP = {OP_SWAP} (idx={_PRIME_IDX[OP_SWAP]})", file=sys.stderr)
                elif current_instruction_pointer_for_processing == 83: # Should be DUP
                    print(f"DEBUG VM (UOR_ADDR {current_instruction_pointer_for_processing}): Expected operation_prime for DUP = {OP_DUP} (idx={_PRIME_IDX[OP_DUP]})", file=sys.stderr)
            if operation_prime is not None:
                op = operation_prime
                
                if op == OP_HALT:
                    halt_for_this_iteration = True
                elif op == OP_PUSH:
                    if current_instruction_pointer_for_processing == 83: # This condition is inside OP_PUSH block
                        print(f"DEBUG VM (UOR_ADDR 83): !!! UNEXPECTEDLY ENTERED OP_PUSH LOGIC !!!", file=sys.stderr)
                        print(f"DEBUG VM (UOR_ADDR 83): Data used for this PUSH misinterpretation: {data}", file=sys.stderr)
                    val_p_for_push = None
                    # op_p_found = False # This variable is not strictly necessary as 'op' is already OP_PUSH
                    for p_val_iter, e_val_iter in data:
                        if p_val_iter == OP_PUSH and e_val_iter == 4:
                            pass # This is the opcode factor itself
                        elif e_val_iter == 5: # Standard exponent for operand in chunk_push
                            val_p_for_push = p_val_iter
                    
                    # Debugging print to show what was identified from logical factors (data)
                    print(f"DEBUG VM: OP_PUSH at UOR_addr {current_instruction_pointer_for_processing}. "
                          f"Logical factors (data) used for operand search: {data}. "
                          f"Identified val_p_for_push (operand prime value): {val_p_for_push}.", file=sys.stderr)

                    if val_p_for_push is None:
                        # Fallback or error for malformed PUSH
                        if len(data) == 1 and data[0][0] == OP_PUSH and data[0][1] > 5 : # e.g. OP_PUSH^9 case
                             val_p_for_push = OP_PUSH # Value pushed would be _PRIME_IDX[OP_PUSH] = 0
                             print(f"DEBUG VM: OP_PUSH UOR_addr {current_instruction_pointer_for_processing} "
                                   f"- Fallback used: val_p_for_push set to OP_PUSH ({OP_PUSH}).", file=sys.stderr)
                        else: 
                             raise ValueError(f"Malformed OP_PUSH chunk at UOR_addr {current_instruction_pointer_for_processing}. "
                                              f"Could not find operand prime with exp 5. Data: {data}")
                    
                    if val_p_for_push not in _PRIME_IDX: # Ensure the identified prime is known
                        # This could happen if _is_prime failed to add it, or if it's not actually prime
                        # but somehow passed other checks. Or if it's a prime from a different system.
                        _extend_primes_to(len(_PRIMES) + 20) # Try to extend primes just in case
                        if val_p_for_push not in _PRIME_IDX: # Check again
                            # Attempt to add it if it's prime and truly missing; this is defensive.
                            if _is_prime(val_p_for_push) and val_p_for_push not in _PRIME_IDX:
                                _PRIMES.append(val_p_for_push)
                                _PRIME_IDX[val_p_for_push] = len(_PRIMES) -1
                                print(f"DEBUG VM: OP_PUSH dynamically added prime {val_p_for_push} to cache.", file=sys.stderr)
                            else:
                                raise ValueError(f"OP_PUSH Error at UOR_addr {current_instruction_pointer_for_processing}: "
                                                f"Operand prime value {val_p_for_push} not found in _PRIME_IDX and could not be added. Data: {data}")

                    value_to_push_idx = _PRIME_IDX[val_p_for_push]
                    
                    print(f"DEBUG VM: OP_PUSH at UOR_addr {current_instruction_pointer_for_processing}. "
                          f"Value to push to stack (prime index): {value_to_push_idx}. "
                          f"Stack BEFORE push: {list(stack)}", file=sys.stderr)
                          
                    stack.append(value_to_push_idx)

                    print(f"DEBUG VM: OP_PUSH at UOR_addr {current_instruction_pointer_for_processing}. "
                          f"Stack AFTER push: {list(stack)}", file=sys.stderr)
                elif op == OP_ADD:
                    if len(stack) < 2: raise ValueError(f"ADD needs 2 values on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    b, a = stack.pop(), stack.pop(); stack.append(a + b)
                elif op == OP_PRINT:
                    if not stack: raise ValueError(f"PRINT needs 1 value on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    output_for_this_iteration = str(stack.pop()) 
                elif op == OP_DUP:
                    if current_instruction_pointer_for_processing == 83:
                        print(f"DEBUG VM (UOR_ADDR 83 OP_DUP): Stack BEFORE DUP: {list(stack)}", file=sys.stderr)
                    if not stack: raise ValueError(f"DUP needs 1 value on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    stack.append(stack[-1])
                    if current_instruction_pointer_for_processing == 83:
                        print(f"DEBUG VM (UOR_ADDR 83 OP_DUP): Stack AFTER DUP: {list(stack)}", file=sys.stderr)
                elif op == OP_SWAP:
                    if current_instruction_pointer_for_processing >= 79 and current_instruction_pointer_for_processing <= 82:
                        print(f"DEBUG VM (UOR_ADDR {current_instruction_pointer_for_processing}): Entered OP_SWAP block. Stack BEFORE swap: {list(stack)}", file=sys.stderr)
                    if len(stack) < 2: raise ValueError(f"SWAP needs 2 values on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    stack[-1], stack[-2] = stack[-2], stack[-1]
                    if current_instruction_pointer_for_processing >= 79 and current_instruction_pointer_for_processing <= 82:
                        print(f"DEBUG VM (UOR_ADDR {current_instruction_pointer_for_processing}): Stack AFTER swap: {list(stack)}", file=sys.stderr)
                elif op == OP_DROP:
                    if not stack: 
                        raise ValueError(f"DROP needs 1 value on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    popped_value = stack.pop()
                elif op == OP_PEEK_CHUNK:
                    if not stack: raise ValueError(f"PEEK_CHUNK needs 1 index on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    idx_to_peek = stack.pop()
                    if not 0 <= idx_to_peek < len(chunks):
                        raise ValueError(f"PEEK_CHUNK: Index {idx_to_peek} out of bounds for program length {len(chunks)} at UOR_addr {current_instruction_pointer_for_processing}")
                    value_peeked = chunks[idx_to_peek]
                    stack.append(value_peeked) 
                elif op == OP_POKE_CHUNK:
                    print(f"--- POKE_CHUNK @{current_instruction_pointer_for_processing} ---", file=sys.stderr)
                    current_stack_snapshot = list(stack)
                    print(f"    Stack upon POKE_CHUNK entry: {current_stack_snapshot} (len: {len(current_stack_snapshot)})", file=sys.stderr)

                    if len(current_stack_snapshot) < 2:
                        raise ValueError(f"POKE_CHUNK needs index and value on stack. Stack: {current_stack_snapshot}")

                    # Pop address
                    idx_to_poke = stack.pop() 
                    print(f"    Popped ADDR: {idx_to_poke}", file=sys.stderr)
                    current_stack_snapshot_after_addr_pop = list(stack)
                    print(f"    Stack after pop ADDR: {current_stack_snapshot_after_addr_pop}", file=sys.stderr)
                    
                    if not stack: 
                        raise ValueError(f"POKE_CHUNK: Stack empty after popping address. Addr was {idx_to_poke}.")

                    # Peek at value before popping
                    value_peeked = stack[-1]
                    print(f"    PEEKED value before pop: {value_peeked} (type: {type(value_peeked)})", file=sys.stderr)

                    # Pop value
                    value_popped = stack.pop()
                    print(f"    POPPED value: {value_popped} (type: {type(value_popped)})", file=sys.stderr)
                    print(f"    Stack after pop VALUE: {list(stack)}", file=sys.stderr)
                                        
                    if not (isinstance(idx_to_poke, int) and 0 <= idx_to_poke < len(chunks)):
                         raise ValueError(f"POKE_CHUNK: Invalid idx_to_poke: {idx_to_poke}")
                    
                    print(f"    chunks[{idx_to_poke}] BEFORE assignment: {chunks[idx_to_poke]}", file=sys.stderr)
                    print(f"    ASSIGNING: chunks[{idx_to_poke}] = {value_popped} (which is value_popped)", file=sys.stderr)
                    
                    chunks[idx_to_poke] = value_popped # THE CRITICAL ASSIGNMENT
                    
                    print(f"    chunks[{idx_to_poke}] AFTER assignment: {chunks[idx_to_poke]}", file=sys.stderr)
                    
                    if chunks[idx_to_poke] != value_popped:
                        print(f"    !!!!!!!! POKE_CHUNK ASSIGNMENT FAILED! "
                              f"Tried to assign {value_popped} but chunks[{idx_to_poke}] became {chunks[idx_to_poke]}", file=sys.stderr)
                    print(f"--- POKE_CHUNK @{current_instruction_pointer_for_processing} END ---", file=sys.stderr)
                elif op == OP_FACTORIZE:
                    if not stack: raise ValueError(f"FACTORIZE needs 1 chunk value on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    chunk_to_factor = stack.pop()
                    factors_of_operand = _factor(chunk_to_factor)
                    logical_factors_of_operand: List[Tuple[int,int]] = []
                    op_pot_chk_p, op_pot_chk_e = None, 0
                    op_temp_fac_for_xor = []
                    for p_f, e_f in factors_of_operand:
                        if e_f >= 6 and op_pot_chk_p is None: op_pot_chk_p, op_pot_chk_e = p_f, e_f
                        else: op_temp_fac_for_xor.append((p_f,e_f))
                    if op_pot_chk_p:
                        xor_v_op = 0
                        for p_vf, e_vf in op_temp_fac_for_xor: 
                            xor_v_op ^= _PRIME_IDX[p_vf]*e_vf
                        if op_pot_chk_p == get_prime(xor_v_op):
                            if op_pot_chk_e > 6: logical_factors_of_operand.append((op_pot_chk_p, op_pot_chk_e-6))
                            logical_factors_of_operand.extend(op_temp_fac_for_xor)
                        else:
                            logical_factors_of_operand.append((op_pot_chk_p, op_pot_chk_e))
                            logical_factors_of_operand.extend(op_temp_fac_for_xor)
                    else:
                        logical_factors_of_operand = factors_of_operand
                    valid_logical_factors = [(p_lf,e_lf) for p_lf,e_lf in logical_factors_of_operand if e_lf > 0]
                    stack.append(len(valid_logical_factors))
                    for p_factor, e_factor in reversed(valid_logical_factors):
                        stack.append(e_factor)            
                        stack.append(_PRIME_IDX[p_factor]) 
                elif op == OP_BUILD_CHUNK:
                    if not stack: raise ValueError(f"BUILD_CHUNK needs count of factor pairs at UOR_addr {current_instruction_pointer_for_processing}")
                    num_factor_pairs = stack.pop()
                    print(f"DEBUG BUILD_CHUNK @{current_instruction_pointer_for_processing}: num_factor_pairs = {num_factor_pairs}. Stack BEFORE loop: {list(stack)}", file=sys.stderr) 
                    
                    if len(stack) < num_factor_pairs * 2:
                        raise ValueError(f"BUILD_CHUNK: Not enough elements on stack for {num_factor_pairs} factor pairs at UOR_addr {current_instruction_pointer_for_processing}.")
                    
                    factors_for_new_chunk: List[Tuple[int,int]] = []
                    raw_val_product = 1 
                    
                    # Use 'pair_num' as the loop variable here
                    for pair_num in range(num_factor_pairs): 
                        p_idx_for_new = stack.pop() 
                        exp_for_new = stack.pop()   
                        print(f"DEBUG BUILD_CHUNK @{current_instruction_pointer_for_processing}: Pair {pair_num + 1}/{num_factor_pairs} - Popped p_idx: {p_idx_for_new}, Popped exp: {exp_for_new}", file=sys.stderr) 
                        
                        if exp_for_new <= 0: 
                            print(f"DEBUG BUILD_CHUNK @{current_instruction_pointer_for_processing}: Pair {pair_num + 1}/{num_factor_pairs} - SKIPPED due to exp ({exp_for_new}) <= 0.", file=sys.stderr) 
                            continue 
                        
                        p_val_for_new = get_prime(p_idx_for_new)
                        factors_for_new_chunk.append((p_val_for_new, exp_for_new))
                        raw_val_product *= (p_val_for_new ** exp_for_new)
                        print(f"DEBUG BUILD_CHUNK @{current_instruction_pointer_for_processing}: Pair {pair_num + 1}/{num_factor_pairs} - Using factor ({p_val_for_new}, {exp_for_new}). Current raw_val_product: {raw_val_product}. factors_for_new_chunk: {factors_for_new_chunk}", file=sys.stderr) 
                    
                    print(f"DEBUG BUILD_CHUNK @{current_instruction_pointer_for_processing}: Final raw_val_product: {raw_val_product}, Final factors_for_new_chunk (to be checksummed): {factors_for_new_chunk}", file=sys.stderr) 
                    new_chunk = _attach_checksum(raw_val_product, factors_for_new_chunk)
                    print(f"DEBUG BUILD_CHUNK @{current_instruction_pointer_for_processing}: Built new_chunk with checksum: {new_chunk}", file=sys.stderr) 
                    stack.append(new_chunk)
                elif op == OP_GET_PRIME:
                    if not stack: raise ValueError(f"GET_PRIME needs 1 index on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    idx_val = stack.pop()
                    stack.append(get_prime(idx_val))
                elif op == OP_GET_PRIME_IDX:
                    if not stack: raise ValueError(f"GET_PRIME_IDX needs 1 prime value on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    prime_val_from_stack = stack.pop()
                    if prime_val_from_stack not in _PRIME_IDX:
                        is_it_prime = _is_prime(prime_val_from_stack) 
                        if not is_it_prime or prime_val_from_stack not in _PRIME_IDX:
                            raise ValueError(f"GET_PRIME_IDX: Value {prime_val_from_stack} is not a known/indexed prime at UOR_addr {current_instruction_pointer_for_processing}.")
                    stack.append(_PRIME_IDX[prime_val_from_stack])
                elif op == OP_NOP:
                    pass
                elif op == OP_COMPARE_EQ:
                    if len(stack) < 2: raise ValueError(f"COMPARE_EQ needs 2 values on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    b, a = stack.pop(), stack.pop()
                    stack.append(PRIME_IDX_TRUE if a == b else PRIME_IDX_FALSE)
                elif op == OP_JUMP:
                    if not stack: raise ValueError(f"JUMP needs 1 target address value on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    target_absolute_address = stack.pop()
                    if not 0 <= target_absolute_address <= len(chunks):
                        raise ValueError(f"JUMP: Target absolute UOR_addr {target_absolute_address} out of bounds for program length {len(chunks)} at UOR_addr {current_instruction_pointer_for_processing}.")
                    i = target_absolute_address
                elif op == OP_JUMP_IF_ZERO:
                    if len(stack) < 2: raise ValueError(f"JUMP_IF_ZERO needs condition and target_address on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    condition_idx = stack.pop()
                    target_absolute_address = stack.pop()
                    
                    if not isinstance(target_absolute_address, int) or not (0 <= target_absolute_address < len(chunks)): # check target bounds
                        raise ValueError(f"JUMP_IF_ZERO: Invalid target address {target_absolute_address} (must be int within program bounds 0-{len(chunks)-1}) at UOR_addr {current_instruction_pointer_for_processing}")

                    if condition_idx == PRIME_IDX_FALSE: # If condition is 0 (false)
                        i = target_absolute_address
                    # else: condition was true (or non-zero), IP just increments past JUMP_IF_ZERO
                elif op == OP_CALL:
                    if not stack:
                        raise ValueError(f"OP_CALL needs a target address on the stack at UOR_addr {current_instruction_pointer_for_processing}")
                    target_address = stack.pop()
                    stack.append(i) 
                    if not 0 <= target_address < len(chunks):
                        raise ValueError(f"OP_CALL: Target address {target_address} out of bounds for program length {len(chunks)} at UOR_addr {current_instruction_pointer_for_processing}")
                    i = target_address
                elif op == OP_RETURN:
                    if not stack:
                        raise ValueError(f"OP_RETURN needs a return address on the stack at UOR_addr {current_instruction_pointer_for_processing}")
                    return_address = stack.pop()
                    if not 0 <= return_address <= len(chunks):
                        raise ValueError(f"OP_RETURN: Return address {return_address} out of bounds for program length {len(chunks)} at UOR_addr {current_instruction_pointer_for_processing}")
                    i = return_address
                elif op == OP_MOD:
                    if len(stack) < 2: 
                        raise ValueError(f"MOD needs 2 values on stack (value, modulus) at UOR_addr {current_instruction_pointer_for_processing}")
                    # Order: stack top is modulus, below it is value. So pop modulus, then value.
                    modulus_idx = stack.pop()
                    value_idx = stack.pop()
                    
                    # We are assuming that PUSH puts prime *indices* on the stack,
                    # and arithmetic operations operate on these indices.
                    
                    # PUSH 0 pushes the prime index 0. So if modulus_idx is 0, it's a mod by the value at prime index 0.
                    if modulus_idx == 0: # Assuming PUSH 0 results in index 0 on stack.
                        raise ValueError(f"Modulo by value represented by prime index 0 attempted at UOR_addr {current_instruction_pointer_for_processing}")
                    
                    result_idx = value_idx % modulus_idx # Perform modulo on the indices
                    stack.append(result_idx) 
                elif op == OP_INPUT:
                    input_value = yield {
                        'ip': i, # IP for the *next* instruction after input is received
                        'stack': list(stack),
                        'program': list(chunks), # Send current program state
                        'output_this_step': None,
                        'halt_flag': False,
                        'error_msg': None,
                        'needs_input': True # Special flag
                    }
                    # When app.py sends a value, it resumes here, and 'input_value' gets that value.
                    if input_value is None:
                        print(f"DEBUG VM: OP_INPUT received None, pushing prime index 0.", file=sys.stderr)
                        stack.append(_PRIME_IDX[get_prime(0)]) # Push prime index 0
                    elif not isinstance(input_value, int):
                        raise ValueError(f"OP_INPUT expected an integer (prime index), but received {type(input_value)}: {input_value}")
                    else:
                        stack.append(input_value) # Push the received prime index onto the stack
                    # 'output_for_this_iteration' remains None for OP_INPUT itself.
                    # The next instruction will operate with the new value on stack.
                    # The outer loop will yield the state *after* OP_INPUT has completed and pushed.
                    # So, we 'continue' here to re-evaluate the 'yield' at the end of the main VM loop,
                    # which will now reflect the stack *after* input_value is pushed.
                    # However, the problem with 'continue' is that the main yield at the end of the loop
                    # would then redundantly yield the state *again* for the OP_INPUT step.
                    #
                    # The current structure of vm_execute is:
                    #   while:
                    #     ip_before_op = i
                    #     op_logic()
                    #     yield state_after_op
                    #
                    # When OP_INPUT hits:
                    #   1. It yields {'needs_input': True}
                    #   2. app.py calls generator.send(value)
                    #   3. OP_INPUT logic resumes, pushes 'value' to stack.
                    #   4. The `vm_execute` loop completes its current iteration.
                    #   5. The standard `yield` at the end of the `vm_execute` loop
                    #      will then reflect the state *after* the input value has been pushed.
                    # This seems correct. No 'continue' needed here. The main yield will handle it.
                    pass # The value is now on the stack. The main loop yield will report the new state.
                elif op == OP_RANDOM:
                    if not stack: 
                        raise ValueError(f"OP_RANDOM needs 1 value (max_exclusive_idx) on stack at UOR_addr {current_instruction_pointer_for_processing}")
                    max_exclusive_idx = stack.pop()
                    if not isinstance(max_exclusive_idx, int) or max_exclusive_idx < 0:
                        raise ValueError(f"OP_RANDOM: max_exclusive_idx must be a non-negative integer. Got {max_exclusive_idx} at UOR_addr {current_instruction_pointer_for_processing}")
                    
                    random_value_idx = 0 # Default if max_exclusive_idx is 0 or 1
                    if max_exclusive_idx > 1:
                        random_value_idx = random.randint(0, max_exclusive_idx - 1)
                    elif max_exclusive_idx == 1: # random.randint(0,0) is fine, but explicit.
                        random_value_idx = 0 
                    # If max_exclusive_idx is 0, random_value_idx remains 0, effectively PUSH 0.
                    
                    stack.append(random_value_idx)
                    print(f"DEBUG VM: OP_RANDOM at UOR_addr {current_instruction_pointer_for_processing}. "
                          f"Popped max_exclusive_idx: {max_exclusive_idx}. Pushed random_value_idx: {random_value_idx}. "
                          f"Stack AFTER: {list(stack)}", file=sys.stderr)
                else: 
                    raise ValueError(f'Unknown opcode prime: {op} at UOR_addr {current_instruction_pointer_for_processing}')
            
            else: # Data chunk (this `else` aligns with `if operation_prime is not None:`)
                char_prime_val = None
                if len(data) == 1 and data[0][1] == 3:
                    char_prime_val = data[0][0]
                elif len(data) == 2:
                    if data[0][1] == 1 and data[1][1] == 2: char_prime_val = data[1][0]
                    elif data[0][1] == 2 and data[1][1] == 1: char_prime_val = data[0][0]
                
                if char_prime_val is not None:
                    if char_prime_val not in _PRIME_IDX:
                        _extend_primes_to(len(_PRIMES) + 5) 
                        if char_prime_val not in _PRIME_IDX:
                            raise ValueError(f"Data char prime {char_prime_val} not in _PRIME_IDX for output at UOR_addr {current_instruction_pointer_for_processing} even after extension attempt.")
                    try:
                        output_for_this_iteration = chr(_PRIME_IDX[char_prime_val])
                    except (OverflowError, ValueError) as e_char:
                        raise ValueError(f"Data char conversion error for prime index {_PRIME_IDX.get(char_prime_val, 'UNKNOWN_PRIME')} at UOR_addr {current_instruction_pointer_for_processing}: {e_char}")
                else:
                    pass 

        except ValueError as e_val:
            error_for_this_iteration = f"ValueError at UOR_addr {current_instruction_pointer_for_processing}: {str(e_val)}"
            halt_for_this_iteration = True 
        except Exception as e_gen:
            import traceback 
            error_for_this_iteration = f"Exception at UOR_addr {current_instruction_pointer_for_processing}: {type(e_gen).__name__} - {str(e_gen)}"
            halt_for_this_iteration = True
        

        if current_instruction_pointer_for_processing == (len(chunks_arg) - 3) and op == OP_POKE_CHUNK and not error_for_this_iteration and not halt_for_this_iteration:

            if current_instruction_pointer_for_processing == 62 and not error_for_this_iteration and not halt_for_this_iteration:
                 print(f"DEBUG VM YIELD (after UOR_instr 62 'POKE_CHUNK to addr 0' was processed): "
                       f"VM's internal chunks[0] = {chunks[0]} (type: {type(chunks[0])}) before yielding program state.", file=sys.stderr)
       
        yield {
            'ip': i, 'stack': list(stack), 'program': list(chunks), 
            'output_this_step': output_for_this_iteration,
            'halt_flag': halt_for_this_iteration, 'error_msg': error_for_this_iteration
        }

        if halt_for_this_iteration or error_for_this_iteration:
            break

    print(f"DEBUG VM: Exiting vm_execute. Stack OBJ ID final: {id(stack)}. Instruction count: {instruction_count}. Final stack: {list(stack)}", file=sys.stderr)

# ──────────────────────────────────────────────────────────────────────
# Tests & Demo
# ──────────────────────────────────────────────────────────────────────
def _self_tests() -> Tuple[int,int]:
    passed=failed=0
    def ok(cond,msg):
        nonlocal passed,failed
        if cond: passed+=1
        else: failed+=1; print(f'FAIL: {msg}', file=sys.stderr)

    # Helper function to run VM and collect results for tests
    def run_vm_for_test(program: List[int]) -> Tuple[str, Dict]:
        collected_output = []
        final_state = {}
        for step_result in vm_execute(program):
            final_state = step_result # Keep the last state
            if step_result.get('output_this_step'):
                collected_output.append(step_result['output_this_step'])
            if step_result.get('halt_flag') or step_result.get('error_msg'):
                break # Stop processing if halted or error
        return "".join(collected_output), final_state

    ok(get_prime(0)==2 and get_prime(1)==3 and get_prime(2)==5, "Core primes (0,1,2) loaded")
    ok(OP_PUSH==2 and OP_ADD==3 and OP_PRINT==5, "Base opcodes match core primes")
    ok(BLOCK_TAG==get_prime(3) and NTT_TAG==get_prime(4) and T_MOD_NTT==get_prime(5), "System tags loaded")
    ok(OP_DUP==get_prime(6) and OP_GET_PRIME_IDX==get_prime(14), "New opcodes loaded")
    ok(OP_HALT==get_prime(19), "OP_HALT loaded correctly")
    ok(OP_RANDOM==get_prime(24), "OP_RANDOM loaded correctly")

    # Test PUSH/PRINT Hi
    try:
        _extend_primes_to(max(ord('H'), ord('i')) + 1)
        program_hi_numeric = [chunk_push(ord('H')), chunk_print(), chunk_push(ord('i')), chunk_print(), chunk_halt()]
        output_str, final_state = run_vm_for_test(program_hi_numeric)
        expected_str_only = str(ord('H')) + str(ord('i'))
        ok(output_str == expected_str_only and final_state.get('halt_flag') and not final_state.get('error_msg'),
           f"PUSH/PRINT Hi test. Expected '{expected_str_only}' then HALT. Got: '{output_str}', Final state: {final_state}")
    except Exception as e:
        ok(False, f"PUSH/PRINT Hi test failed: {e}")

    # Test ADD
    try:
        _extend_primes_to(10) 
        val1_idx = 8 
        val2_idx = 9 
        program_add = [chunk_push(val1_idx), chunk_push(val2_idx), chunk_add(), chunk_print(), chunk_halt()]
        output_str, final_state = run_vm_for_test(program_add)
        expected_str_only = str(val1_idx + val2_idx)
        ok(output_str == expected_str_only and final_state.get('halt_flag') and not final_state.get('error_msg'),
           f"ADD test. Expected '{expected_str_only}' then HALT. Got: '{output_str}', Final state: {final_state}")
    except Exception as e:
        ok(False, f"ADD test failed: {e}")

    # Test NTT with HALT
    try:
        _extend_primes_to(30) 
        idx_p10, idx_p20, idx_p30 = 10, 20, 30
        ntt_inner_prog = [
            chunk_push(idx_p10), chunk_push(idx_p20), chunk_push(idx_p30),
            chunk_print(), chunk_print(), chunk_print(),
            chunk_halt() # Halt within the NTT block
        ]
        ntt_prog_numeric = [chunk_ntt(len(ntt_inner_prog))] + ntt_inner_prog
        output_str, final_state = run_vm_for_test(ntt_prog_numeric)
        expected_str_only = str(idx_p30) + str(idx_p20) + str(idx_p10)
        ok(output_str == expected_str_only and final_state.get('halt_flag') and not final_state.get('error_msg'),
           f"NTT passthrough with inner HALT. Expected '{expected_str_only}' then HALT. Got: '{output_str}', Final state: {final_state}")
    except Exception as e:
        ok(False, f"NTT passthrough test failed: {e}")

    # Test CALL and RETURN
    try:
        _extend_primes_to(max(100, 50, 8))
        prog_call_ret = [
            chunk_push(6), chunk_call(), chunk_push(100), chunk_print(), chunk_halt(),
            chunk_nop(), chunk_push(50), chunk_print(), chunk_return()
        ]
        output_str, final_state = run_vm_for_test(list(prog_call_ret)) # Use a copy
        expected_str_only = str(50) + str(100)
        ok(output_str == expected_str_only and final_state.get('halt_flag') and not final_state.get('error_msg'),
           f"CALL/RETURN test. Expected '{expected_str_only}' then HALT. Got: '{output_str}', Final state: {final_state}")
    except Exception as e:
        import traceback
        ok(False, f"CALL/RETURN test failed: {e}\n{traceback.format_exc()}")

    # Test JUMP to HALT
    try:
        _extend_primes_to(20)
        target_halt_address = 3 
        _extend_primes_to(target_halt_address)
        prog_jump_to_halt = [
            chunk_push(target_halt_address), chunk_jump(), chunk_nop(), chunk_halt()
        ]
        output_str, final_state = run_vm_for_test(list(prog_jump_to_halt)) # Use a copy
        expected_str_only = "" # No output expected before HALT
        ok(output_str == expected_str_only and final_state.get('halt_flag') and not final_state.get('error_msg'),
           f"JUMP to HALT. Expected no output then HALT. Got: '{output_str}', Final state: {final_state}")
    except Exception as e:
        import traceback
        ok(False, f"JUMP to HALT test failed: {e}\n{traceback.format_exc()}")
    

    # Test OP_RANDOM
    try:
        _extend_primes_to(5)
        program_random = [chunk_push(3), chunk_random(), chunk_print(), chunk_halt()]
        random_results = set()
        all_halted_ok = True
        for _ in range(20): 
            output_str, final_state = run_vm_for_test(list(program_random))
            if not (final_state.get('halt_flag') and not final_state.get('error_msg')):
                all_halted_ok = False; break
            try:
                val = int(output_str)
                if not (0 <= val < 3):
                    all_halted_ok = False; break # Value out of expected bounds
                random_results.add(val)
            except ValueError:
                all_halted_ok = False; break # Output not an int

        ok(all_halted_ok and len(random_results) > 0 and all(0 <= r < 3 for r in random_results),
           f"OP_RANDOM(3) test. Expected values in [0,2]. Got: {random_results}, Halted OK: {all_halted_ok}")

        program_random_edge = [chunk_push(1), chunk_random(), chunk_print(), chunk_halt()]
        output_str_edge, final_state_edge = run_vm_for_test(list(program_random_edge))
        ok(output_str_edge == "0" and final_state_edge.get('halt_flag') and not final_state_edge.get('error_msg'),
           f"OP_RANDOM(1) test. Expected '0'. Got: '{output_str_edge}', Halted OK: {final_state_edge.get('halt_flag')}")

    except Exception as e:
        import traceback
        ok(False, f"OP_RANDOM test failed: {e}\n{traceback.format_exc()}")

    ok(chunk_nop() > 1, "chunk_nop() produces a non-trivial chunk")
    ok(chunk_halt() > 1, "chunk_halt() produces a non-trivial chunk")

    return passed,failed

if __name__=='__main__':

    p,f=_self_tests()
    print(f'\n[tests] {p} passed, {f} failed.') # Added a period for consistency.
    if f:
        pass 

    print("\n--- Demo ---")
    _extend_primes_to(ord('🎉') + 10) 
    sample = "Pure UOR demo 🎉"
    
    # Helper function for demo execution, similar to test helper
    def run_vm_for_demo(program: List[int]):
        collected_output = []
        final_state = {}
        print("▶ VM Execution Start...")
        for step_idx, step_result in enumerate(vm_execute(program)):
            final_state = step_result
            if step_result.get('output_this_step'):
                collected_output.append(step_result['output_this_step'])
            if step_result.get('halt_flag') or step_result.get('error_msg'):
                break
        print("▶ VM Execution End.")
        return "".join(collected_output), final_state

    print("\nDemo 1: PUSHing ord(char) as prime indices, OP_PRINT prints these indices as numbers.")
    numeric_char_code_stream = []
    for char_val in sample:
        numeric_char_code_stream.extend([chunk_push(ord(char_val)), chunk_print()])
    numeric_char_code_stream.append(chunk_halt())
    
    print(f"▶ Demo 1: Encoding chunks (PUSH ord, PRINT, HALT):")
    # print(f"Generated {len(numeric_char_code_stream)} chunks for Demo 1: {numeric_char_code_stream}") # Optional: print chunks
    print("▶ Demo 1: Decoded output (numeric char codes):")
    
    demo1_output_str, demo1_final_state = run_vm_for_demo(numeric_char_code_stream)
    
    print(' '.join(list(demo1_output_str)))
    print(' '.join(demo1_output_str.split()))
    print(' '.join(run_vm_for_demo(numeric_char_code_stream)[0].split()))
    
    collected_demo1_prints = []
    final_demo1_state_for_print = {}
    for step_result in vm_execute(numeric_char_code_stream):
        final_demo1_state_for_print = step_result
        if step_result.get('output_this_step'):
            collected_demo1_prints.append(step_result['output_this_step'])
        if step_result.get('halt_flag') or step_result.get('error_msg'):
            break
    print(' '.join(collected_demo1_prints))

    if demo1_final_state.get('halt_flag') and not demo1_final_state.get('error_msg'):
        print("[VM_HALTED_SUCCESSFULLY]")
    elif demo1_final_state.get('error_msg'):
        print(f"[VM_ERROR_STATE: {demo1_final_state['error_msg']}]")
    else: # Should be halted if program ends correctly
        print("[VM_FINISHED_UNEXPECTEDLY_WITHOUT_HALT_OR_ERROR]")

    print("\nDemo 2: Using chunk_data to represent a string.")
    data_chunk_stream = []
    for i, char_val in enumerate(sample):
        data_chunk_stream.append(chunk_data(i, ord(char_val)))
    data_chunk_stream.append(chunk_halt())
    
    print(f"▶ Demo 2: Encoding chunks (chunk_data per char, HALT):")
    # print(f"Generated {len(data_chunk_stream)} chunks for Demo 2: {data_chunk_stream}") # Optional
    print("▶ Demo 2: Decoded text (using chunk_data):")

    demo2_output_str, demo2_final_state = run_vm_for_demo(data_chunk_stream)
    print(demo2_output_str)

    if demo2_final_state.get('halt_flag') and not demo2_final_state.get('error_msg'):
        print("[VM_HALTED_SUCCESSFULLY]")
    elif demo2_final_state.get('error_msg'):
        print(f"[VM_ERROR_STATE: {demo2_final_state['error_msg']}]")
    else:
        print("[VM_FINISHED_UNEXPECTEDLY_WITHOUT_HALT_OR_ERROR]")