#include "reasoning.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void reasoning_init() {
    printf("[REASONING] Initializing ReAct engine...\n");
}

bool process_reasoning_step(const char* input, react_step_t* step) {
    /* Parse a "Thought: <text> | Action: <token>" string produced by the
     * Cloud Brain.  All buffers are bounded to prevent overruns. */

    if (!strstr(input, "Thought:") || !strstr(input, "Action:")) {
        return false;
    }

    /* --- Parse Thought field ---
     * We scan at most (sizeof(step->thought) - 1) chars, then always
     * null-terminate so the buffer is safe regardless of input length. */
    char thought_fmt[32];
    snprintf(thought_fmt, sizeof(thought_fmt), "Thought: %%%d[^|]", (int)(sizeof(step->thought) - 1));
    if (sscanf(input, thought_fmt, step->thought) != 1) {
        return false;
    }
    step->thought[sizeof(step->thought) - 1] = '\0';

    /* Trim any trailing whitespace left by the %[^|] match */
    int len = (int)strlen(step->thought);
    while (len > 0 && (step->thought[len - 1] == ' ' || step->thought[len - 1] == '\t')) {
        step->thought[--len] = '\0';
    }

    /* --- Parse Action field ---
     * Locate the delimiter and copy at most sizeof(params)-1 bytes. */
    const char* action_ptr = strstr(input, "| Action:");
    if (!action_ptr) {
        return false;
    }
    action_ptr += strlen("| Action:");
    while (*action_ptr == ' ') action_ptr++;  /* skip leading spaces */

    strncpy(step->action.params, action_ptr, sizeof(step->action.params) - 1);
    step->action.params[sizeof(step->action.params) - 1] = '\0';

    /* Trim trailing newline / whitespace */
    int plen = (int)strlen(step->action.params);
    while (plen > 0 && (step->action.params[plen - 1] == '\n' ||
                        step->action.params[plen - 1] == '\r' ||
                        step->action.params[plen - 1] == ' ')) {
        step->action.params[--plen] = '\0';
    }

    /* Map action string to tool_id */
    if (strcmp(step->action.params, "MOVE") == 0)        step->action.id = TOOL_MOVE_ARM;
    else if (strcmp(step->action.params, "GRIP") == 0)   step->action.id = TOOL_GRIPPER;
    else if (strcmp(step->action.params, "SENSOR") == 0) step->action.id = TOOL_READ_SENSORS;
    else if (strcmp(step->action.params, "STATUS") == 0) step->action.id = TOOL_SAY_STATUS;
    else                                                  step->action.id = TOOL_UNKNOWN;

    return true;
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
