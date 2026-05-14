#include <<stdiostdio.h>
#include "reasoning.h"
#include "nvs_manager.h"

int main() {
    printf("--- OpenClaw Robotic System Firmware ---\\n");

    robot_config_t config;
    nvs_reset_defaults();
    nvs_load_config(&config);
    printf("Device ID: %s\\n", config.device_id);

    reasoning_init();

    const char* mock_llm_response = "Thought: The object is at (10,20). I need to move the arm. | Action: MOVE";
    react_step_t step;

    if (process_reasoning_step(mock_llm_response, &step)) {
        printf("Thought: %s\\n", step.thought);
        dispatch_tool(step.action);
    }

    return 0;
}
