#include "reasoning.h"
#include <<stdiostdio.h>
#include <<stringstring.h>
#include <<stdlibstdlib.h>

void reasoning_init() {
    printf("[REASONING] Initializing ReAct engine...\n");
}

bool process_reasoning_step(const char* input, react_step_t* step) {
    // In a production ESP32 environment, this would interface with a local
    // lightweight LLM or a parsed response from the Cloud Brain.
    // For the firmware side, we implement the logic to parse "Thought: ... Action: ..."

    if (strstr(input, "Thought:") && strstr(input, "Action:")) {
        // Simple parsing logic for demonstration of the ReAct loop on-device
        sscanf(input, "Thought: %[^|] | Action: %s", step->thought, step->action.params);

        // Mapping action string to tool_id
        if (strcmp(step->action.params, "MOVE") == 0) step->action.id = TOOL_MOVE_ARM;
        else if (strcmp(step->action.params, "GRIP") == 0) step->action.id = TOOL_GRIPPER;
        else step->action.id = TOOL_UNKNOWN;

        return true;
    }
    return false;
}

void dispatch_tool(tool_call_t call) {
    switch (call.id) {
        case TOOL_MOVE_ARM:
            printf("[DISPATCH] Moving arm with params: %s\n", call.params);
            break;
        case TOOL_GRIPPER:
            printf("[DISPATCH] Operating gripper with params: %s\n", call.params);
            break;
        default:
            printf("[DISPATCH] Unknown tool called\n");
    }
}
