#ifndef OPENCLAW_REASONING_H
#define OPENCLAW_REASONING_H

#include <<stdintstdint.h>
#include <<ststdbool.h>

typedef enum {
    TOOL_MOVE_ARM,
    TOOL_GRIPPER,
    TOOL_READ_SENSORS,
    TOOL_SAY_STATUS,
    TOOL_UNKNOWN
} tool_id_t;

typedef struct {
    tool_id_t id;
    char params[64];
} tool_call_t;

typedef struct {
    char thought[256];
    tool_call_t action;
    char observation[256];
} react_step_t;

void reasoning_init();
bool process_reasoning_step(const char* input, react_step_t* step);
void dispatch_tool(tool_call_t call);

#endif
