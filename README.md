# PrimeOS - Autonomous Goal-Seeking & Self-Modifying VM

## Introduction

PrimeOS is a unique Virtual Machine (VM) project demonstrating the concept of "living code." The VM executes programs where instructions are represented by prime number factorizations (Universal Object Representation - UOR). The core demonstration showcases a UOR program that autonomously modifies its own instructions in a continuous loop, adapting its behavior to achieve externally set numerical goals. These goals are provided by an adaptive "Teacher" component in the backend. This iteration of the project expands the self-modification capabilities to include not just changing instruction operands but also altering instruction types in pre-defined "slots" within the code.

## Approach

1.  **Universal Object Representation (UOR):** Instructions and data are not represented by fixed bytecodes but by integers derived from the unique factorization of prime numbers. Each instruction or data chunk has a distinct numerical representation based on specific primes raised to specific exponents. This allows for a flexible and mathematically grounded instruction set.
2.  **Self-Modification at Multiple Levels:**
    *   **Operand Modification:** The primary "guessing" instruction (a `PUSH` operation at address 0) has its operand (the value it pushes) directly modified by the UOR program itself based on success/failure feedback.
    *   **Instruction Type Replacement:** On persistent failure, the UOR program can change the *type* of instruction in a designated "modification slot" (e.g., at address 1). It can randomly choose to replace the existing instruction with a `PUSH(0)`, an `ADD`, or a `NOP`, thereby altering its computational structure.
3.  **Prime-Based Integrity:** UOR chunks incorporate checksums also based on prime factorizations, ensuring structural integrity during decoding and execution.
4.  **Autonomous Goal-Seeking with a Teacher:** The system employs a "Teacher-Learner" model. The UOR program ("Learner") attempts to achieve goals (output specific numbers). The Python backend ("Teacher") provides these goals, gives feedback, and adaptively changes the difficulty of the goals based on the Learner's performance.

## Process (The Learning Loop)

The interaction between the UOR program (Learner) and the Flask backend (Teacher) drives the self-modification and learning:

1.  **Initialization:**
    *   The Teacher (in `app.py`) selects an initial numerical target.
    *   It then pre-modifies the Learner's UOR program by POKEing a `PUSH(initial_target)` instruction into Address 0.
    *   A specific 4-element stack is prepared for the Learner, carrying state like the last poked value, failure count, and information about the last modification slot.

2.  **Learner's Attempt:**
    *   The UOR program begins execution.
    *   The instruction at Address 0 (the `PUSH` instruction) places its current attempt value onto the stack.
    *   The instruction at Address 1 (the "modification slot," initially a `NOP`) is executed.
    *   The Learner `PRINT`s its resulting numerical guess.

3.  **Feedback Request:**
    *   The Learner executes an `OP_INPUT` instruction, pausing and requesting feedback from the Teacher.

4.  **Teacher's Evaluation & Feedback:**
    *   The Teacher (`app.py`) compares the Learner's printed guess with the current target.
    *   It sends back a "success" or "failure" signal to the Learner via the `OP_INPUT` channel.

5.  **Learner's Adaptation (Self-Modification):**

    *   **On Success:**
        1.  The Learner requests a *new target* from the Teacher (another `OP_INPUT`).
        2.  The Teacher provides a new target (adjusting difficulty if needed).
        3.  The Learner uses `BUILD_CHUNK` to create a new `PUSH(new_target)` instruction.
        4.  It uses `POKE_CHUNK` to **overwrite its own instruction at Address 0** with this new `PUSH` instruction.
        5.  It resets its internal failure count and jumps back to the beginning of its main loop.

    *   **On Failure:**
        1.  The Learner increments its internal failure count.
        2.  If "stuck" (too many consecutive failures), it `PRINT`s a "99" signal.
        3.  **It calculates a new operand** for its `PUSH` instruction at Address 0 using a randomized incremental search.
        4.  **It randomly chooses an instruction type** (`PUSH(0)`, `ADD`, or `NOP`).
        5.  It uses `BUILD_CHUNK` to create this chosen instruction.
        6.  It uses `POKE_CHUNK` to **overwrite its own instruction at Address 1** (the modification slot) with this new instruction.
        7.  It then uses `BUILD_CHUNK` to create the `PUSH(new_calculated_operand)` instruction.
        8.  It uses `POKE_CHUNK` to **overwrite its own instruction at Address 0** with this modified `PUSH` instruction.
        9.  It jumps back to the beginning of its main loop.

6.  **Loop:** The process repeats, with the Learner continually refining its Address 0 `PUSH` instruction and experimenting with the instruction in Address 1 to achieve the Teacher's targets.

## Features

*   **Novel Virtual Machine (UOR):**
    *   Dynamic prime caching for efficient UOR instruction decoding.
    *   Rich instruction set including arithmetic, stack operations, control flow (`JUMP`, `JUMP_IF_ZERO`), interaction (`OP_INPUT`), randomness (`OP_RANDOM`), and self-modification (`POKE_CHUNK`, `BUILD_CHUNK`).
    *   Checksums for UOR chunk integrity.
*   **Complex Self-Modifying UOR Program (~225 instructions):**
    *   Modifies its primary `PUSH` instruction's operand at Address 0.
    *   On failure, modifies the instruction *type* at a "modification slot" (Address 1) by POKEing a `PUSH(0)`, `ADD`, or `NOP`.
    *   Persists state (last poked values, failure counts, last chosen slot/instruction type) across modification cycles.
*   **Autonomous Goal-Seeking:**
    *   Sophisticated interaction loop with the Teacher via `OP_INPUT`.
    *   Adapts to success by requesting and adopting new goals.
    *   Implements strategies for failure including randomized search, repetition avoidance, and a "stuck" signal.
*   **Adaptive "Teacher" (`app.py`):**
    *   Sets external numerical goals.
    *   Provides success/failure feedback.
    *   Implements adaptive teaching: adjusts goal difficulty (range of numbers) based on the VM's performance (quick successes vs. struggles).
*   **Web-Based Visualization & UI (Flask & JavaScript):**
    *   Frontend for initializing the VM, stepping through instructions (manually or auto-step).
    *   Displays:
        *   Current "action" explanation based on UOR program logic.
        *   Large, prominent display of the VM's last numerical output.
        *   The current UOR instruction being executed (address, raw chunk, decoded).
        *   VM stack content.
        *   VM output log.
        *   VM status (IP, Halted, Error, Target, Difficulty).
    *   Retro "hacker" themed UI for a more engaging experience.
*   **Backend Logging:** Detailed logging of VM initialization, steps, inputs, and state changes in `log.txt`.

## Future Improvements

*   **A. More Sophisticated Ways to Decide What Code to Generate (Driven by Feedback/Goals):**
    *   **Current State (as of `goal_seeker_demo.uor.txt`):** The system has a solid feedback loop where the UOR program modifies its primary `PUSH` instruction's operand based on success/failure in hitting an externally set target. On failure, it employs a randomized incremental search for the next operand. On success, it adopts the new target provided by the Teacher.
    *   **Planned Enhancements:**
        *   **Advanced Failure Strategies within UOR:** Instead of just a simple incremental search on failure, the UOR program could implement more complex strategies. For example, it could:
            *   Maintain a memory of past failed attempts for a specific target to avoid repeating them or to try a different search pattern (e.g., binary search if applicable, or larger random jumps).
            *   Analyze the *magnitude* of the error (how far off its guess was) to make more informed adjustments to its next attempt.
        *   **Adaptive Teacher Enhancements:** The `app.py` Teacher could become more sophisticated in how it sets goals, perhaps by:
            *   Observing patterns in the VM's struggles or successes to present targets that specifically challenge or reinforce certain learned behaviors.
            *   Introducing sequences of related goals rather than purely random ones.

*   **B. Different Strategies for Modification (Beyond Overwriting One PUSH Instruction):**
    *   **Current State:** The UOR program primarily modifies the operand of the `PUSH` instruction at Address 0 and, on failure, can change the entire instruction type (to `PUSH(0)`, `ADD`, or `NOP`) at the `MODIFICATION_SLOT_0` (Address 1).
    *   **Planned Enhancements:**
        *   **Targeting Other Instructions/Slots:** Enable the UOR program to decide to modify instructions at *different addresses* or in *multiple modification slots*. This could involve a UOR-level "pointer" to the instruction it wants to change.
        *   **Modifying Different Instruction *Types*:** Beyond just the `PUSH` operand or swapping instructions in a slot, allow the UOR to learn to modify the operands of other instruction types (e.g., changing the value in a different `PUSH`, or an operand for a hypothetical `STORE` or `LOAD` instruction if added).
        *   **Code Insertion/Deletion:** A more advanced (and complex) goal would be for the UOR program to be able to insert new instructions into its sequence or delete existing ones, dynamically changing its length and overall structure. This would require careful management of jump targets and program flow.
        *   **Parameterized Slot Modification:** Instead of always POKEing `PUSH(0)` into a slot, allow the UOR to decide the operand for the `PUSH` instruction it builds for a slot, potentially based on context or learned strategy.

*   **C. An Ability to Reason About Its Own Code Structure at a Higher Level:**
    *   **Current State:** The UOR program executes instructions that result in self-modification but doesn't possess an abstract understanding of its own code. It doesn't "know" it's modifying a `PUSH` instruction, only that it's building and POKEing specific UOR chunk values.
    *   **Planned Enhancements (More Ambitious/Long-Term):**
        *   **Internal Decompilation/Analysis:** Equip the UOR program with sequences of instructions that allow it to use `PEEK_CHUNK` to read an instruction, `FACTORIZE` to understand its components (opcode, operands), and then make decisions based on this analysis. For example, "If the instruction at slot X is an ADD, and I'm failing, maybe I should change it to a PUSH."
        *   **Abstract Code Representation:** Develop a way for the UOR to build or manipulate a higher-level (or intermediate) representation of its code or code fragments, allowing for more planned and structured modifications.
        *   **Goal-Oriented Code Construction:** Instead of just random choices for slot modification, the UOR could learn or be guided to select instruction types or sequences that are more likely to help achieve the current numerical goal based on some internal model or learned heuristics.
        *   **Evolutionary/Genetic Algorithms within UOR:** Explore having the UOR program manage populations of small code snippets or parameters, applying evolutionary pressures (selection based on success) to "evolve" better solutions or sub-routines internally.

## File List & Usage

```
├── backend/
│ ├── uor_programs/
│ │ └── goal_seeker_demo.uor.txt # Generated UOR program
│ ├── init.py
│ └── app.py # Flask backend, "Teacher" logic
├── frontend/
│ ├── css/
│ │ └── style.css # Styles for the UI
│ ├── js/
│ │ ├── api.js # Frontend API call utilities
│ │ ├── main.js # Main UI logic, event handling
│ │ └── ui_updater.js # Updates UI elements with VM state
│ └── index.html # Main HTML page for the UI
├── generate_goal_seeker_uor.py # Python script to generate the UOR program
├── phase1_vm_enhancements.py # Core PrimeOS VM logic, opcodes, UOR constructors
└── README.md # This file
```

**How to Run:**

1.  **Generate the UOR Program (if not present or if modified):**
    Open a terminal in the project root directory and run:
    ```bash
    python generate_goal_seeker_uor.py
    ```
    This will create/update `backend/uor_programs/goal_seeker_demo.uor.txt`.

2.  **Run the Flask Web Application (Teacher & VM Backend):**
    In the same terminal, run:
    ```bash
    python backend/app.py
    ```
    The Flask development server will start, typically on `http://127.0.0.1:5000/`.

3.  **Access the Frontend:**
    Open your web browser and navigate to `http://127.0.0.1:5000/`.

4.  **Interact with the Demo:**
    *   Click **"Initialize PrimeVM"** to load the UOR program and set up the VM.
    *   Click **"Step Instruction"** to execute one instruction at a time.
    *   Click **"Autostep"** to let the VM run automatically. The "Current Action" and other displays will update live.
    *   Click **"Stop Autostep"** to pause automatic execution.

    Watch how the "Current Action" describes the VM's internal decisions and how the "Program Memory (Current Instruction)" might change, especially the instruction at Address 0 or Address 1. The "Large Output Display" shows the VM's latest numerical guess.

## Requirements

*   Python 3.7+
*   Flask (install via `pip install Flask`)
